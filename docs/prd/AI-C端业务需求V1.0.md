# AI-C端业务需求V1.0 副本

## 背景

基于市场C端应用发展趋势分析应用研究以及Ai赛道快速发展现状，决定开始以及C端Ai生图业务为起点，同步开启IAP业务探索及AI中台能力积累，为后续快速迭代项目打下基础。

## 目标

- 完成AI中台搭建 V1.0
  - 考虑可拓展性、通用性、实用性
- 定义C端Ai-Human Photo Studio产品V1.0版本

## 项目收益

- 验证C端IAP类型产品策略
- AI赛道生图方向建立产品站位

## 项目详情

### C端：PicKitchen

**AI-Powered Avatars, Emojis & Poses**

#### 背景：

图片的模型基座能力仍期待完善，但Ai生图对于传统图片处理给予技术侧更多的想象空间，可以低成本高效率提供围绕图片的丰富玩法，打造有趣的体验。

### V1.0需求

设计figma：

<table>
<thead>
<tr>
<th>功能</th>
<th>交互</th>
<th>说明</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>首页(P0)</strong></td>
<td>image.png</td>
<td>
<ul>
<li>顶tab支持图片和视频，视频在V1.0暂不展示。</li>
<li>注意支持多tab框架，后续迭代Voice，Music</li>
<li>顶tab支持滑动切换，切换新的内容</li>
<li>all先隐藏</li>
<li>顶部Banner交互
<ul>
<li>支持Banner配置跳转功能（端上写死）</li>
<li>Banner图</li>
<li>图片文字</li>
<li>banner顺序</li>
<li>banner自动切换间隔2秒</li>
</ul>
</li>
<li>Emoji Chicken
<ul>
<li>Emoji合成功能</li>
<li>视频封面图</li>
<li>视频/图片内容</li>
<li>放在本地，每次打开自动加载</li>
<li>风格名称-服务端下发</li>
<li>https://help.aliyun.com/zh/model-studio/emoji-api?spm=a2c4g.11186623.help-menu-2400256.d_2_3_13_1.6d6972dac0zxoX&scm=20140722.H_2865374._.OR_help-T_cn~zh-V_1#552aacbdadtaq</li>
</ul>
</li>
<li>分类功能点击，页面从底部弹起，展开分类功能入口详情</li>
</ul>
</td>
</tr>
<tr>
<td><strong>Emoji功能（P0）</strong></td>
<td>image.png</td>
<td>
<ul>
<li>Emoji功能
<ul>
<li>Server技术文档：图生表情包技术文档</li>
</ul>
</li>
<li>上传图片
<ul>
<li>点击上传：调起本地相册</li>
<li>图片样例提示：
<ul>
<li>正面示例：正面完整头像</li>
<li>反面示例：遮挡人像，侧面人像，多人照片</li>
<li>设计师提供</li>
</ul>
</li>
</ul>
</li>
<li>图片检测
<ul>
<li>上传图片后，自动检测</li>
<li>检测调阿里云官方检测接口</li>
<li>图片检测通过后
<ul>
<li>积分足够进入自动生成</li>
<li>积分不够
<ul>
<li>会员状态，调起积分购买页</li>
<li>非会员状态，调起付费墙</li>
</ul>
</li>
</ul>
</li>
<li>检测不通过，停留当前页面
<ul>
<li>提示图片有问题</li>
</ul>
</li>
</ul>
</li>
<li>生成Emoji 动画
<ul>
<li>生成动画</li>
<li>可以采取渐隐渐现</li>
</ul>
</li>
<li>完成页
<ul>
<li>加载当前生成视频</li>
<li>不展示视频时长</li>
</ul>
</li>
<li>完成
<ul>
<li>点击完成，关闭页面，返回到上层级页面</li>
</ul>
</li>
<li>重新生成
<ul>
<li>返回生成动画页</li>
<li>扣减积分</li>
</ul>
</li>
<li>生成逻辑
<ul>
<li>生成任务开启时，消耗200积分</li>
<li>积分根据任务类型可由Server配置调整积分</li>
<li>生成任务暂时以设备id由Server存储积分数据</li>
</ul>
</li>
</ul>
</td>
</tr>
<tr>
<td><strong>分类页能力（P0）</strong></td>
<td>image.png</td>
<td>
<ul>
<li>顶tab
<ul>
<li>分类名称，封面图本地存储</li>
</ul>
</li>
</ul>
</td>
</tr>
<tr>
<td><strong>会员主页</strong></td>
<td>image.png<br><br>image.png</td>
<td>
<ul>
<li>会员态
<ul>
<li>用户是会员时，有特殊会员标识</li>
<li>无会员时，标识置灰</li>
</ul>
</li>
<li>历史概览
<ul>
<li>提交一次生成时的内容</li>
<li>分图片和视频</li>
<li>视频展示第一帧作为封面图</li>
<li>有视频标识</li>
</ul>
</li>
<li>点击积分
<ul>
<li>若已开启会员：跳转积分详情页</li>
<li>若用户不是会员，调起付费墙</li>
</ul>
</li>
<li>会员详情页：选择积分包
<ul>
<li>积分包对应奖励积分有Server下发配置</li>
</ul>
</li>
<li>点击购买
<ul>
<li>调起ios/安卓购买页</li>
</ul>
</li>
</ul>
</td>
</tr>
<tr>
<td><strong>付费墙</strong></td>
<td>image.png</td>
<td>
<ul>
<li>付费引导页面</li>
<li>付费墙时机：
<ul>
<li>上传图片检测通过后，非会员调起付费墙</li>
<li>个人中心，非会员点击积分调起付费墙</li>
</ul>
</li>
<li>顶部效果图支持自动轮播
<ul>
<li>支持视频或者图片</li>
<li>视频自动播放，播放完成后切换到下一个内容</li>
<li>图片停留3秒后切换</li>
</ul>
</li>
<li>图片文案：主标题+副标题</li>
<li>订阅方案
<ul>
<li>默认选择第一项</li>
<li>点击调起IOS/Google订阅能力，完成订阅</li>
</ul>
</li>
<li>交互效果
<ul>
<li>顶部引导图给定尺寸，文案给定位置，后续根据功能引导配置配置引导效果图</li>
</ul>
</li>
<li>权益说明文案
<ul>
<li>Enhance，Colorize，Animate faster</li>
<li>Remove All Function Limits</li>
<li>Extra Points Discount</li>
<li>No ads</li>
</ul>
</li>
<li>订阅方案
<ul>
<li>积分奖励</li>
<li>Weekly pass
<ul>
<li>3 days free trail</li>
</ul>
</li>
<li>iAP策略@zm计算emoji成本</li>
</ul>
</li>
<li>订阅
<ul>
<li>3日免费试用，3日后自动开启周会员</li>
<li>每周2000积分，支持Server配置</li>
</ul>
</li>
<li>终生会员，一次性付费
<ul>
<li>每周3000积分，支持Server配置</li>
</ul>
</li>
<li>内购
<ul>
<li>内购商品
<ul>
<li>1000积分 2.99美金</li>
<li>3000积分 7.99美金</li>
<li>10000积分 20.99美金</li>
</ul>
</li>
<li>测试期间，价格待测算</li>
</ul>
</li>
</ul>
</td>
</tr>
</tbody>
</table>
