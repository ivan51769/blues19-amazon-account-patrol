# 环境安装与配置

官方依据：[紫鸟 CLI 官方页面](https://open.ziniao.com/ziniaoCli)及其[安装指南](https://open.ziniao.com/docSupport?docId=281)。本文件在官方 CLI 步骤之外，补充本巡检脚本自身的 Python 和店铺可见性检查。

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

紫鸟官方要求先安装 **Node.js 16 或更高版本**。检查版本后，再全局安装 CLI 和官方 Skills：

```powershell
node -v
npm install -g @ziniao-open/cli
ziniao-cli --version
npx skills add ziniao-open/skills -y
```

全局安装会修改系统环境，后续初始化会写入授权配置。让 AI Agent 执行时，必须先取得用户批准，并在沙盒外运行；否则全局安装可能无法持久化，后续命令也可能读取不到授权配置。

在 PowerShell 执行策略阻止 `.ps1` 启动器时，直接使用 `npm.cmd` 和 `ziniao-cli.cmd`，不要降低系统执行策略：

```powershell
node -v
npm.cmd install -g @ziniao-open/cli
ziniao-cli.cmd --version
npx.cmd skills add ziniao-open/skills -y
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

### Boss 与子账号

- Boss 账号可使用企业级管理 API，并控制已授权的紫鸟浏览器能力。
- 紫鸟子账号需先由 Boss 授权，才能通过自然语言或 CLI 操作其有权访问的浏览器和店铺；不能执行卖家自研应用的企业级权限配置。
- 本巡检只需要目标店铺的浏览器访问权限，不应扩大为企业管理权限。

## 可选：继续扩展更多紫鸟 Skill

`blues19-amazon-account-patrol` 的主任务是九市场只读巡检，`ziniao-cli` 只是它复用店铺浏览器会话的桥接依赖。安装官方紫鸟 Skills 后，还可以在现有权限和接口边界内，为其他业务闭环制作独立 Skill。

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

默认只写本地记录，不发送消息。只有用户明确要求时才添加 `--send-feishu`，并通过环境变量提供凭证和默认群聊：

```powershell
$env:FEISHU_APP_ID = '<app-id>'
$env:FEISHU_APP_SECRET = '<app-secret>'
$env:FEISHU_CHAT_ID = '<chat-id>'
```

也可以在运行时使用 `--feishu-chat-id` 指定目的群。不要把这些值提交到 Skill 或源代码。

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
