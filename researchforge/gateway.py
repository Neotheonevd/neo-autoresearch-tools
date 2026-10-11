"""Loopback budget gate for OpenAI and Anthropic text/tool protocols."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import secrets
import urllib.request
from urllib.parse import urlsplit

from .protocol import to_openai, to_anthropic, anthropic_events
from .store import Halt, encoded


def make_server(store, config, port=18764, *, transport=None):
    # Config stores environment variable NAMES, never real provider keys.
    upstream_key = os.environ[config['upstream_key_env']]
    base = config['upstream_base_url'].rstrip('/')
    if not base.startswith('https://'):
        raise ValueError('HTTPS upstream required')
    routes=[]
    for category,row in config['categories'].items():
        token=os.environ[row['token_env']]
        if len(token)<24:raise ValueError('local capability token too short')
        routes.append((token,category,row['model']))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,status,value):
            body=encoded(value).encode();self.send_response(status)
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
            self.end_headers();self.wfile.write(body)
        def route(self):
            supplied=self.headers.get('x-api-key') or self.headers.get('Authorization','').removeprefix('Bearer ')
            return next(((category,model) for token,category,model in routes if secrets.compare_digest(token,supplied)),None)
        def do_GET(self):
            route=self.route()
            if not route:return self.reply(401,{'error':'unauthorized'})
            if self.path=='/v1/models':return self.reply(200,{'object':'list','data':[{'id':route[1],'object':'model','owned_by':'configured-provider'}]})
            if self.path=='/health':return self.reply(200,{'mode':store.snapshot()['mode']})
            self.reply(404,{'error':'unknown route'})
        def do_POST(self):
            route=self.route()
            if not route:return self.reply(401,{'error':{'type':'authentication_error','message':'unauthorized'}})
            call=None
            try:
                route_path=urlsplit(self.path).path
                if route_path not in {'/v1/messages','/v1/chat/completions'}:
                    return self.reply(404,{'error':{'type':'invalid_request_error','message':'unsupported route'}})
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=4000000:raise ValueError('request size limit')
                body=json.loads(self.rfile.read(size));category,model=route
                if body.get('model')!=model:raise ValueError('model differs from frozen route')
                anthropic=route_path=='/v1/messages';stream=body.get('stream',False)
                request=to_openai(body,model) if anthropic else dict(body)
                request.pop('stream',None);request.pop('stream_options',None)
                if request.get('n',1)!=1:raise ValueError('multiple generations unsupported')
                maximum=request.get('max_tokens',4096)
                if type(maximum) is not int or not 1<=maximum<=8192:raise ValueError('output reservation limit')
                request['max_tokens']=maximum
                call=store.reserve(category,request,len(encoded(request).encode())+maximum)
                upstream=urllib.request.Request(base+'/chat/completions',data=encoded(request).encode(),
                    headers={'Content-Type':'application/json','Authorization':'Bearer '+upstream_key})
                try:
                    with (transport or urllib.request.urlopen)(upstream,timeout=120) as response:result=json.load(response)
                    usage=result.get('usage',{});tokens=usage.get('total_tokens')
                    if type(tokens) is not int or tokens<0:raise ValueError('provider omitted authoritative usage')
                    # Validate translation before releasing a response. Usage is
                    # already known if translation fails; don't call it unknown.
                    store.settle(call,tokens);call=None
                except Exception as exc:
                    if call:store.uncertain(call,'provider result unavailable: '+type(exc).__name__);call=None
                    raise Halt('provider failure; paused for reconciliation') from exc
                converted=to_anthropic(result) if anthropic else result
                if not stream:return self.reply(200,converted)
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Connection','close');self.end_headers()
                if anthropic:
                    for name,event in anthropic_events(converted):
                        self.wfile.write(('event: '+name+'\ndata: '+encoded(event)+'\n\n').encode())
                else:
                    choice=result['choices'][0];delta=dict(choice['message'])
                    for i,tool in enumerate(delta.get('tool_calls',[])):tool['index']=i
                    base_chunk={k:result[k] for k in ['id','model','created'] if k in result};base_chunk['object']='chat.completion.chunk'
                    chunks=[{**base_chunk,'choices':[{'index':0,'delta':delta,'finish_reason':None}]},
                            {**base_chunk,'choices':[{'index':0,'delta':{},'finish_reason':choice.get('finish_reason')}],'usage':result['usage']}]
                    for chunk in chunks:self.wfile.write(('data: '+encoded(chunk)+'\n\n').encode())
                    self.wfile.write(b'data: [DONE]\n\n')
                self.wfile.flush();self.close_connection=True
            except Halt as exc:
                self.reply(429,{'type':'error','error':{'type':'rate_limit_error','message':str(exc)}})
            except (ValueError,KeyError,TypeError) as exc:
                if call:store.uncertain(call,'local processing interrupted')
                self.reply(400,{'type':'error','error':{'type':'invalid_request_error','message':str(exc)}})
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    return server


def serve(store, config, port=18764):
    server=make_server(store,config,port)
    try:server.serve_forever()
    finally:server.server_close()
