# PicKitchen V1.0 后端技术需求

## 1. 概述

本文档梳理 PicKitchen V1.0 产品中涉及后端开发的功能点和接口需求。

---

## 2. 配置管理服务

### 2.1 首页Tab配置

| 配置项 | 类型 | 说明 |
|--------|------|------|
| tab_order | array | Tab顺序 |
| tab_name | string | Tab名称 |
| tab_enabled | boolean | 开关状态 |

**接口需求**：
- 获取Tab配置列表

### 2.2 Banner配置

| 配置项 | 类型 | 说明 |
|--------|------|------|
| banner_image | string | Banner图片URL |
| banner_text | string | 图片文字 |
| banner_order | int | Banner顺序 |
| jump_url | string | 跳转链接 |

**接口需求**：
- 获取Banner配置列表

### 2.3 风格配置

| 配置项 | 类型 | 说明 |
|--------|------|------|
| style_id | string | 风格ID |
| style_name | string | 风格名称 |
| style_image | string | 风格封面图 |
| category | string | 所属分类 |

**接口需求**：
- 获取风格列表（支持分类筛选）

---

## 3. Emoji生成服务

### 3.1 图片检测

**功能**：检测上传图片是否符合要求（正面完整头像）

**检测规则**：
- 必须包含人脸
- 必须是正面头像
- 不能有遮挡
- 不能是侧面
- 不能包含多人

**接口需求**：
- 图片检测接口（返回检测结果和错误原因）

### 3.2 Emoji生成

**功能**：调用阿里云API生成表情包

**技术文档**：[阿里云Emoji API](https://help.aliyun.com/zh/model-studio/emoji-api?spm=a2c4g.11186623.help-menu-2400256.d_2_3_13_1.6d6972dac0zxoX&scm=20140722.H_2865374._.OR_help-T_cn~zh-V_1#552aacbdadtaq)

**接口需求**：
- 创建生成任务接口
- 查询任务状态接口
- 获取生成结果接口

**任务状态**：
| 状态 | 说明 |
|------|------|
| pending | 等待处理 |
| processing | 生成中 |
| completed | 生成完成 |
| failed | 生成失败 |

---

## 4. 积分系统

### 4.1 积分配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| emoji_cost | int | Emoji生成消耗积分 | 200 |
| weekly_reward | int | 周会员每周奖励积分 | 2000 |
| lifetime_reward | int | 终生会员每周奖励积分 | 3000 |

**接口需求**：
- 获取积分配置

### 4.2 积分管理

**数据存储**：
- 初期：以设备ID存储积分数据（本地优先）
- 后期：迁移至服务端存储

**接口需求**：
- 查询用户积分余额
- 扣减积分（生成任务时）
- 增加积分（购买/订阅奖励）
- 积分流水记录查询

### 4.3 积分流水

| 字段 | 类型 | 说明 |
|------|------|------|
| device_id | string | 设备ID |
| change_type | enum | 变动类型（consume/reward/purchase） |
| change_amount | int | 变动数量 |
| balance | int | 变动后余额 |
| task_type | string | 关联任务类型 |
| created_at | timestamp | 创建时间 |

---

## 5. 会员系统

### 5.1 会员状态

| 字段 | 类型 | 说明 |
|------|------|------|
| device_id | string | 设备ID |
| member_type | enum | 会员类型（none/weekly/lifetime） |
| expire_time | timestamp | 过期时间 |
| is_trial | boolean | 是否试用期 |

**接口需求**：
- 查询会员状态
- 更新会员状态（IAP回调）

### 5.2 订阅方案配置

| 方案 | product_id | 价格 | 试用期 | 积分奖励 |
|------|------------|------|--------|----------|
| Weekly Pass | weekly_pass | - | 3天 | 2000/周 |
| 终生会员 | lifetime_member | - | 无 | 3000/周 |

### 5.3 内购商品配置

| 商品 | product_id | 价格 | 积分数量 |
|------|------------|------|----------|
| 积分包1 | points_1000 | $2.99 | 1000 |
| 积分包2 | points_3000 | $7.99 | 3000 |
| 积分包3 | points_10000 | $20.99 | 10000 |

**接口需求**：
- 获取商品列表
- IAP购买验证（iOS/Android）
- 购买成功回调处理

---

## 6. 历史记录服务

### 6.1 生成记录

| 字段 | 类型 | 说明 |
|------|------|------|
| record_id | string | 记录ID |
| device_id | string | 设备ID |
| type | enum | 类型（image/video） |
| source_image | string | 原图URL |
| result_url | string | 生成结果URL |
| style_id | string | 使用的风格ID |
| created_at | timestamp | 创建时间 |

**接口需求**：
- 获取历史记录列表（分页）
- 删除历史记录

---

## 7. 热门作品服务（V1.0不做）

> 注：此功能V1.0暂不实现，仅做接口预留

**接口需求**：
- 获取热门作品列表（随机返回）
- 运营后台：添加/删除热门作品

---

## 8. 接口汇总

### 8.1 配置类接口

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 获取Tab配置 | GET | /api/v1/config/tabs | 首页Tab配置 |
| 获取Banner配置 | GET | /api/v1/config/banners | Banner列表 |
| 获取风格列表 | GET | /api/v1/config/styles | 风格配置 |
| 获取积分配置 | GET | /api/v1/config/points | 积分规则配置 |
| 获取商品列表 | GET | /api/v1/config/products | IAP商品列表 |

### 8.2 业务类接口

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 图片检测 | POST | /api/v1/emoji/detect | 检测图片是否合规 |
| 创建生成任务 | POST | /api/v1/emoji/generate | 创建Emoji生成任务 |
| 查询任务状态 | GET | /api/v1/emoji/task/{task_id} | 查询生成进度 |

### 8.3 用户类接口

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 查询积分余额 | GET | /api/v1/user/points | 获取积分余额 |
| 积分流水 | GET | /api/v1/user/points/history | 积分变动记录 |
| 查询会员状态 | GET | /api/v1/user/member | 会员信息 |
| 历史记录列表 | GET | /api/v1/user/history | 生成历史 |
| 删除历史记录 | DELETE | /api/v1/user/history/{id} | 删除记录 |

### 8.4 支付类接口

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| iOS购买验证 | POST | /api/v1/payment/ios/verify | 验证iOS收据 |
| Android购买验证 | POST | /api/v1/payment/android/verify | 验证Google收据 |

---

## 9. 第三方服务依赖

| 服务 | 用途 | 文档 |
|------|------|------|
| 阿里云Model Studio | Emoji生成 | [Emoji API文档](https://help.aliyun.com/zh/model-studio/emoji-api) |
| Apple App Store | iOS IAP | Apple Developer |
| Google Play | Android IAP | Google Play Console |

---

## 10. 数据存储设计

### 10.1 数据表

| 表名 | 说明 |
|------|------|
| config_tabs | Tab配置表 |
| config_banners | Banner配置表 |
| config_styles | 风格配置表 |
| config_products | 商品配置表 |
| user_points | 用户积分表 |
| user_points_log | 积分流水表 |
| user_member | 会员信息表 |
| user_history | 生成历史表 |
| emoji_tasks | 生成任务表 |

### 10.2 缓存策略

| 数据 | 缓存时间 | 说明 |
|------|----------|------|
| Tab配置 | 5分钟 | 变更不频繁 |
| Banner配置 | 5分钟 | 变更不频繁 |
| 风格列表 | 10分钟 | 变更不频繁 |
| 商品列表 | 10分钟 | 变更不频繁 |
| 用户积分 | 不缓存 | 实时性要求高 |
