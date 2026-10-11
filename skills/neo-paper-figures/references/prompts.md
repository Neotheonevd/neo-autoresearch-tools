# Reusable prompts from Neo's figure iterations

These prompts preserve the user's preferences without reproducing private
conversation logs. The method-specific examples are illustrative, not universal
architecture requirements.

## Main method figure

> 请按照我的手绘逻辑画论文主图。英文用 Comic Sans MS；浅色分组背景、细线条、
> 紧凑排版。地图、Reader、关系分析和 Judger 都需要有具体图形信息，不要只画
> 几个模块名。Reader 和关系分析上下并行，不是前后承接。箭头尽量短而清楚。
> 更多用图表示，文字只做简短标注。先保证结构正确，再优化美学。

## Candidate explanation population

> Judger 需要画出维护一个种群的感觉：每个个体是一个候选错误及其责任解释。
> 展示不同解释的比较，以及每轮从 Reader 和关系分析取得新证据后如何保留、
> 修改或删除候选。不要把它画成一条只会越来越长的历史解释。

## Motivation figure

> 左边从日志展开四五个节点，举出源头错误、传播错误、独立错误、已纠正错误、
> 无关错误。用放大镜突出需要寻找的责任错误；独立错误只有影响最终失败时才
> 承担责任。右边对比不提供解释，以及只维护单一错误解释而不断强化它的情况，
> 再表示多候选解释比较。文字少一点，结构紧密一点，用图表达差别。

## Compactness revision

> 不需要占满整个 PPT 页面。缩小内部空隙，增加有意义的信息量，而不是把图拉宽。
> 标题统一一个字号，其他标注统一较小字号；标题可以斜体。节点、图标和标签
> 应当互相靠近，箭头不要绕路。保留清晰层级和阅读顺序。

## Paper insertion and copyable output

> 动机图做成竖版，压紧，按论文单栏实际宽度检查可读性。论文主图可以双栏。
> 同时保留整页 PPTX，图本身的布局不变，方便复制到自己的幻灯片；另给论文用
> 的紧边界 PDF/PNG。最终交付只保留约定的定稿版本。

## Semantic review before delivery

> 对照手绘和方法说明，检查串行/并行、反馈方向、候选更新和最终输出是否一致。
> 不要为了美观改变算法关系，不要把尚未验证的方案画成已证实的能力。
