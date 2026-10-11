"""Small, explicit Anthropic/OpenAI bridge for text and tool calls.

Images and unknown content blocks fail closed. This adapter is not advertised
as a complete replacement for every provider-specific Anthropic feature.
"""
import json


def to_openai(body, model):
    if body.get('thinking',{}).get('type') in {'enabled','adaptive'}:
        raise ValueError('extended-thinking signature parity is not implemented; use native Anthropic endpoint for this mode')
    messages=[]
    system=body.get('system')
    if system:
        if isinstance(system,list):
            if any(b.get('type')!='text' for b in system):raise ValueError('non-text system content unsupported')
            system='\n'.join(b['text'] for b in system)
        messages.append({'role':'system','content':system})
    for message in body.get('messages',[]):
        role=message['role']
        if role not in {'user','assistant'}:raise ValueError('unsupported role')
        blocks=message['content']
        if isinstance(blocks,str):blocks=[{'type':'text','text':blocks}]
        text=[];tools=[];results=[];reasoning=[]
        for block in blocks:
            kind=block['type']
            if kind=='text':text.append(block['text'])
            elif kind=='thinking':reasoning.append(block['thinking'])
            elif kind=='tool_use' and role=='assistant':
                tools.append({'id':block['id'],'type':'function','function':{'name':block['name'],'arguments':json.dumps(block['input'],ensure_ascii=False)}})
            elif kind=='tool_result' and role=='user':
                content=block.get('content','')
                if isinstance(content,list):
                    if any(x.get('type')!='text' for x in content):raise ValueError('non-text tool result unsupported')
                    content='\n'.join(x['text'] for x in content)
                results.append({'role':'tool','tool_call_id':block['tool_use_id'],'content':content})
            else:raise ValueError('unsupported content block: '+kind)
        # Tool replies must follow their assistant call before new user text.
        messages.extend(results)
        if text or tools or reasoning:
            row={'role':role,'content':'\n'.join(text)}
            if tools:row['tool_calls']=tools
            if reasoning:row['reasoning_content']='\n'.join(reasoning)
            messages.append(row)
    request={'model':model,'messages':messages,'max_tokens':body.get('max_tokens',4096),'stream':False}
    if 'temperature' in body:request['temperature']=body['temperature']
    if 'stop_sequences' in body:request['stop']=body['stop_sequences']
    if body.get('tools'):
        request['tools']=[{'type':'function','function':{'name':tool['name'],'description':tool.get('description',''),'parameters':tool['input_schema']}} for tool in body['tools']]
    if body.get('tool_choice'):
        choice=body['tool_choice']
        if choice['type'] in {'auto','any','none'}:request['tool_choice']={'auto':'auto','any':'required','none':'none'}[choice['type']]
        elif choice['type']=='tool':request['tool_choice']={'type':'function','function':{'name':choice['name']}}
        else:raise ValueError('unsupported tool choice')
    return request


def to_anthropic(response):
    choice=response['choices'][0];message=choice['message'];blocks=[]
    # No invented signature for upstream private reasoning. Return observable
    # text/tool outputs only; this bridge does not claim extended-thinking parity.
    if message.get('content'):blocks.append({'type':'text','text':message['content']})
    for call in message.get('tool_calls',[]):
        blocks.append({'type':'tool_use','id':call['id'],'name':call['function']['name'],'input':json.loads(call['function']['arguments'])})
    usage=response['usage'];details=usage.get('prompt_tokens_details',{})
    cached=details.get('cached_tokens',0)
    return {'id':response['id'],'type':'message','role':'assistant','model':response['model'],'content':blocks,
            'stop_reason':{'stop':'end_turn','tool_calls':'tool_use','length':'max_tokens'}.get(choice.get('finish_reason'),'end_turn'),
            'stop_sequence':None,'usage':{'input_tokens':max(0,usage['prompt_tokens']-cached),'output_tokens':usage['completion_tokens'],
                                        'cache_read_input_tokens':cached,'cache_creation_input_tokens':0}}


def anthropic_events(message):
    initial={**message,'content':[],'stop_reason':None,'usage':{**message['usage'],'output_tokens':0}}
    yield 'message_start',{'type':'message_start','message':initial}
    for index,block in enumerate(message['content']):
        initial_block={**block,'text':''} if block['type']=='text' else {**block,'input':{}}
        yield 'content_block_start',{'type':'content_block_start','index':index,'content_block':initial_block}
        delta={'type':'text_delta','text':block['text']} if block['type']=='text' else {'type':'input_json_delta','partial_json':json.dumps(block['input'],ensure_ascii=False)}
        yield 'content_block_delta',{'type':'content_block_delta','index':index,'delta':delta}
        yield 'content_block_stop',{'type':'content_block_stop','index':index}
    yield 'message_delta',{'type':'message_delta','delta':{'stop_reason':message['stop_reason'],'stop_sequence':None},'usage':{'output_tokens':message['usage']['output_tokens']}}
    yield 'message_stop',{'type':'message_stop'}
