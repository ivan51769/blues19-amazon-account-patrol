# 环境安装与配置

官方依据：[紫鸟 CLI 官方页面](https://open.ziniao.com/ziniaoCli)、[CLI 创建应用和授权流程](https://open.ziniao.com/docSupport?docId=281#%E4%B8%80%E3%80%81%E5%89%8D%E7%BD%AE%E9%80%9A%E7%94%A8%E5%BF%85%E5%81%9A%E4%BA%8B%E9%A1%B9%EF%BC%88%E6%93%8D%E4%BD%9C%E5%89%8D%E4%BC%98%E5%85%88%E6%89%A7%E8%A1%8C%EF%BC%890)及[成员店铺授权说明](https://www.ziniao.com/help/docs/team/17363304414278)。本文件在官方 CLI 步骤之外，补充本巡检脚本自身的 Python、店铺可见性和可选飞书检查。

> 推荐顺序：先完成下方 Node.js、`ziniao-cli`、授权和店铺可见性检查，再安装 `blues19-amazon-account-patrol`，最后验证 Python 脚本。

## 安装 Skill 本体（环境验证后）

将当前完整文件夹安装到智能体的 Skills 目录，安装后的目录名必须为 `blues19-amazon-account-patrol`，并完整保留 `SKILL.md`、`agents/`、`scripts/`、`references/`、`assets/` 与 `tests/`。不要只复制 `SKILL.md`；否则界面元数据、确定性运行脚本、验证用例和按需加载的参考资料都会缺失。

安装后应能通过 `$blues19-amazon-account-patrol` 触发，并在 Skill 目录中完成以下本体检查：

```powershell
Test-Path .\SKILL.md
Test-Path .\agents\openai.yaml
Test-Path .\scripts\amazon_account_patrol.py
python scripts\amazon_account_patrol.py --help
python -m unittest discover -s tests -v
```

## 必需环境

### 1. Python 3.10 或更高版本

脚本仅使用 Python 标准库，不需要单独安装 `requirements.txt`。先检查：

```powershell
python --version
```

如果 Windows 上使用 `--timezone` 和 `--working-hours` 时提示找不到 IANA 时区，再安装时区数据：

```powershell
python -m pip install tzdata
```

未启用工作时段限制时，不要求额外安装 `tzdata`。

### 2. Node.js 与 ziniao-cli

紫鸟官方要求先安装 **Node.js 16 或更高版本**。检查版本后，再全局安装本巡检必需的 CLI：

```powershell
node -v
npm install -g @ziniao-open/cli
ziniao-cli --version
```

全局安装会修改系统环境，后续初始化会写入授权配置。让 AI Agent 执行时，必须先取得用户批准，并在沙盒外运行；否则全局安装可能无法持久化，后续命令也可能读取不到授权配置。

在 PowerShell 执行策略阻止 `.ps1` 启动器时，直接使用 `npm.cmd` 和 `ziniao-cli.cmd`，不要降低系统执行策略：

```powershell
node -v
npm.cmd install -g @ziniao-open/cli
ziniao-cli.cmd --version
```

脚本优先读取环境变量 `ZINIAO_CLI`，否则从 `PATH` 查找 `ziniao-cli.cmd` 或 `ziniao-cli`。不要把个人安装目录写入 Skill。

### 3. 紫鸟浏览器与 ZClaw Bridge

启动紫鸟浏览器客户端，并确保目标店铺可以在本机打开。巡检依赖本地 ZClaw Bridge（通常为 `127.0.0.1:9481`），不会直接调用该地址，而是统一通过 `ziniao-cli` 访问。

### 4. 初始化与验证顺序

首次使用先在沙盒外后台执行初始化：

```powershell
ziniao-cli config init --new
```

该命令会输出浏览器授权链接，并等待应用创建或审批完成。AI Agent 应把授权链接展示给用户，由用户在浏览器完成授权，然后继续等待命令结束。出现链接只说明流程已开始；必须等命令明确显示配置保存成功，才能视为初始化完成。凭证由 CLI 保存，不要写入 Skill、日志或命令参数。

完成后检查：

```powershell
ziniao-cli doctor
ziniao-cli config show
ziniao-cli store list --format table
```

官网指定使用 `doctor` 验证 CLI 配置。此 Skill 另外要求 `config show` 确认当前 profile，并用 `store list` 确认当前成员确实能看到目标店铺。三者不能互相替代。

### 5. BOSS 账号与成员账号

紫鸟官方将 **CLI 应用创建** 与 **店铺资源授权** 分开管理，不要把两者混为一次授权。

| 账号 | 创建 CLI 应用 | 应用何时生效 | 额外职责 |
| --- | --- | --- | --- |
| BOSS 账号 | 可以自行创建 | 填写名称、勾选所需权限并提交后即可创建 | 在开放平台控制台的“应用审核”中审核成员创建的 CLI 应用。 |
| 成员账号 | 可以自行创建 | 通过初始化授权链接登录后会自动创建，但必须由 BOSS 审核通过后才生效 | 只能使用其紫鸟账号原本获授的店铺、云号和浏览器访问范围。 |

按下面顺序操作：

1. 初始化前确认紫鸟客户端与开放平台登录的是准备使用 CLI 的同一账号；账号不一致时，切换后重新运行 `config init --new`。
2. BOSS 账号按页面提示填写应用名称、选择本 Skill 所需权限并提交。
3. 成员账号完成授权链接登录后暂停，通知 BOSS 进入“开放平台控制台 → 应用审核”，确认状态为“审核通过”。CLI 应用审核不能由普通店铺管理员替代。
4. 第一台设备首次初始化时会自动添加本机终端；更换电脑或新增设备时，在“用户应用管理 → 对应 CLI 应用 → 设置 → 终端管理”中录入紫鸟浏览器终端识别码。
5. 应用生效后执行 `store list`。若目标店铺不可见，请 BOSS、超级管理员或具备相应账号管理权限的管理员在成员管理中补充店铺授权，再重新验证。

> 应用审核通过不等于自动新增店铺权限。本巡检只需要目标店铺的浏览器只读访问，以及读取页面和保存截图的能力；不要为它申请员工管理、店铺授权、修改、删除或其他企业管理权限。

官方学习入口：[紫鸟 CLI 创建应用和授权流程](https://open.ziniao.com/docSupport?docId=281#%E4%B8%80%E3%80%81%E5%89%8D%E7%BD%AE%E9%80%9A%E7%94%A8%E5%BF%85%E5%81%9A%E4%BA%8B%E9%A1%B9%EF%BC%88%E6%93%8D%E4%BD%9C%E5%89%8D%E4%BC%98%E5%85%88%E6%89%A7%E8%A1%8C%EF%BC%890)、[成员店铺授权说明](https://www.ziniao.com/help/docs/team/17363304414278)、[管理员角色说明](https://www.ziniao.com/help/docs/team/team_FAQ/17363300634892)。

## 可选：继续扩展更多紫鸟 Skill

`blues19-amazon-account-patrol` 的主任务是九市场只读巡检，`ziniao-cli` 只是它复用店铺浏览器会话的桥接依赖。安装官方紫鸟 Skills 后，还可以在现有权限和接口边界内，为其他业务闭环制作独立 Skill。

官方 Skills 属于扩展能力，不是本巡检的必需环境。需要扩展时再安装：

```powershell
npx.cmd skills add ziniao-open/skills -y
```

[紫鸟官网 Ziniao CLI 页](https://open.ziniao.com/ziniaoCli)当前展示的“真实业务场景回放”包括：

- 新员工入职与店铺授权：列店铺、创建员工、授权店铺、离职回收。
- 网页访问策略：登记 URL、创建白名单、限制下载、绑定店铺。
- 差评 24 小时响应：抓取差评、AI 分类归因、多语种回复草稿、告警看板。
- 亚马逊基础报告：整合订单、库存、流量与广告数据形成运营日报。

官网还把 Listing 维护、库存巡检、批量截图列为可继续按分步引导扩展的日常流程。这些是扩展方向，不代表本巡检 Skill 已经内置这些能力。

当本机已安装 `ziniao-skill-maker` 时，可以把下面一句话发给智能体：

> 请使用 `$ziniao-skill-maker`，把“`<业务场景>`”制作成一个名为 `ziniao-<名称>` 的可复用 Skill。先检查现有 `ziniao-cli` 快捷命令，不够时再使用通用 API 或 ZClaw 页面能力；先给我只读方案、所需权限和验证标准。任何创建、授权、修改、删除、发送或批量操作都必须在执行前向我确认。Skill 必须依赖 `ziniao-shared`，不写入店铺 ID、凭证或个人路径，并附安装、触发、验证和失败停止说明。

制作顺序保持简单：先定义一个业务闭环和成功标准，优先复用现有命令，再补 API 或页面能力；只读流程先验证，写操作必须确认；最后用脱敏测试数据验证最小闭环。官网案例属于紫鸟官方展示，自定义 Skill 的目录结构与安全流程属于本机 Skill 工具约定，两者不要混为一谈。

## Seller Central 前置状态

- 目标紫鸟店铺必须已保存自己的 Amazon 登录账号和密码。
- 如需 MFA，OTP 必须由现有浏览器集成自动填入；脚本不会接收或手工输入 OTP。
- 运行前确认目标成员已获授权访问该店铺。
- 不要在配置文件或 Skill 中保存店铺 ID；运行时通过 `--store-id` 传入。

## 可选：飞书推送

默认只写本地记录，不发送消息。这里使用的是 **飞书企业自建应用 OpenAPI**，不是群自定义机器人 Webhook，也不要求安装 `lark-cli` 或飞书 Codex 插件。

### 1. 先在飞书开发者后台准备应用

1. 创建或选择企业自建应用，在“凭证与基础信息”中由用户本人查看 App ID 和 App Secret。
2. 开启“机器人”能力，申请“以应用的身份发消息”以及“获取与上传图片或文件资源”所需的最小权限。
3. 发布应用版本，并把机器人加入用户确认的目标群；机器人必须在群内且有发言权限。
4. 确认目标群的 `chat_id`。不要猜测收件群，也不要把真实群 ID 写进仓库。

官方依据：[发送消息 API](https://open.feishu.cn/document/server-docs/im-v1/message/create?lang=zh-CN)、[上传图片 API](https://open.feishu.cn/document/server-docs/im-v1/image/create?lang=zh-CN)和[群机器人使用说明](https://open.feishu.cn/document/client-docs/bot-v3/how-to-use-bot-in-feishu)。

### 2. 由用户本人在本机设置凭证

只有用户明确要求时才添加 `--send-feishu`。App Secret 不要粘贴到对话中；由用户本人在将要运行脚本的同一个 PowerShell 窗口设置环境变量：

```powershell
$env:FEISHU_APP_ID = '<app-id>'
$env:FEISHU_APP_SECRET = '<app-secret>'
$env:FEISHU_CHAT_ID = '<已确认的群聊-id>'
```

也可以在运行时使用 `--feishu-chat-id` 指定目的群。AI Agent 只能检查变量是否存在，不能回显变量值；不要把这些值提交到 Skill、源代码、日志或截图。

### 3. 发送前再次确认，发送后分两层验收

测试发送也是外部写操作。执行前再次向用户确认目的群、测试内容和是否允许发送。只有飞书接口返回 `code = 0` 且结果中的 `message_ids` 非空，才能报告“API 已受理”；随后仍要由用户到目标群确认消息和图片实际可见。

把下面这句话直接发给 Codex：

> 请协助我为 `blues19-amazon-account-patrol` 配置可选飞书推送。先确认本地巡检已能运行；说明这套推送使用飞书企业自建应用 OpenAPI。指导我在飞书开发者后台创建或检查自建应用、开启机器人能力、申请“以应用身份发消息”和“获取与上传图片或文件资源”所需的最小权限、发布版本，并把机器人加入我确认的目标群。App ID、App Secret 只由我本人在本机 PowerShell 环境变量中填写，不粘贴到对话、源码或日志；检查时不得回显值。确认群聊 ID 与测试内容后，必须再次取得我的明确批准才能发送测试。只有接口返回 `code = 0` 且 `message_ids` 非空时，才能报告 API 已受理，并提醒我到群内确认实际可见。

## 运行前最小检查

```powershell
python --version
node -v
ziniao-cli --version
ziniao-cli doctor
ziniao-cli config show
ziniao-cli store list --format table
python scripts\amazon_account_patrol.py --help
python -m unittest discover -s tests -v
```

只有版本、认证、Bridge、目标店铺可见性、脚本参数检查和测试都通过后，才进入实际巡检。
