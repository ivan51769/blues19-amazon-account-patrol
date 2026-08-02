<div align="center">
  <img src="assets/wechat-logo.jpg" width="180" alt="拾玖说跨境AI">
  <h1>blues19-amazon-account-patrol</h1>
  <p>通过紫鸟店铺现有浏览器会话，对 Amazon Seller Central 执行可验证、只读的账号健康与绩效通知巡检。</p>
</div>

## 能做什么

- 巡检 Amazon Seller Central 的账号健康和绩效通知页面。
- 覆盖美国、加拿大、墨西哥、英国、德国、法国、意大利、西班牙和荷兰 9 个市场。
- 验证当前工作台国家、域名或 Marketplace ID，避免巡检错站点。
- 保存实际页面 URL、页面原文、截图路径、Markdown 记录和运行日志。
- 默认只保存到本地；只有用户明确要求时才发送到飞书。

> 本 Skill 的主体是 `blues19-amazon-account-patrol`；[`ziniao-cli`](https://open.ziniao.com/ziniaoCli) 是连接紫鸟浏览器店铺会话的必需运行环境。**请先安装并验证 ziniao-cli，再安装本 Skill。**

## 使用顺序

1. 安装 Node.js 16+ 与 `ziniao-cli`。
2. 完成 CLI 授权，并通过 `doctor`、`config show` 和 `store list` 验证。
3. 安装 `blues19-amazon-account-patrol`。
4. 确认 Python 3.10+，再选择店铺与市场运行巡检。

## 第一步：准备 ziniao-cli 环境

需要紫鸟浏览器客户端、可访问的目标店铺，以及 Node.js 16 或更高版本。Windows PowerShell：

```powershell
node -v
npm.cmd install -g @ziniao-open/cli
ziniao-cli.cmd --version
ziniao-cli.cmd config init --new
ziniao-cli.cmd doctor
ziniao-cli.cmd config show
ziniao-cli.cmd store list --format table
```

如果已经安装 CLI，可以跳过全局安装，但仍需完成后续四项验证。全局安装和授权会修改本机配置；如果让智能体执行，应先取得用户批准，授权链接必须由用户本人在浏览器中完成。

完整步骤见 [环境安装与配置](references/setup.md)。

## 第二步：安装本 Skill

ziniao-cli 环境验证通过后，再安装 Skill。

Windows PowerShell：

```powershell
npx.cmd skills add ivan51769/blues19-amazon-account-patrol -y
```

macOS / Linux：

```bash
npx skills add ivan51769/blues19-amazon-account-patrol -y
```

也可以把下面这句话直接发给智能体：

> 请先检查并准备 ziniao-cli 运行环境：确认 Node.js 16+，如缺少 `@ziniao-open/cli`，先说明需要执行的全局安装与授权操作，取得我的批准后再完成；使用 `config init --new` 初始化，并以 `doctor`、`config show` 和 `store list` 验证配置与目标店铺可见性。环境通过后，再从 https://github.com/ivan51769/blues19-amazon-account-patrol 安装完整 Skill，安装名称必须是 `blues19-amazon-account-patrol`，并保留 `SKILL.md`、`agents`、`scripts`、`references`、`assets` 和 `tests`。最后验证 Python 3.10+、脚本 `--help` 和全部测试。不要写入真实店铺 ID、账号凭证或飞书密钥。

## 第三步：运行巡检

巡检脚本要求 Python 3.10 或更高版本，并且只使用标准库。

先查询当前成员可见的店铺：

```powershell
ziniao-cli.cmd store list --format table
```

巡检单个市场：

```powershell
python scripts\amazon_account_patrol.py `
  --store-id <ziniao-store-id> `
  --marketplace us
```

巡检全部 9 个市场：

```powershell
python scripts\amazon_account_patrol.py `
  --store-id <ziniao-store-id> `
  --all-marketplaces
```

支持的市场代码：

| 区域 | 市场代码 |
| --- | --- |
| 北美 | `us`、`ca`、`mx` |
| 欧洲 | `uk`、`de`、`fr`、`it`、`es`、`nl` |

在支持 Skill 的智能体中，也可以直接说：

> 使用 `$blues19-amazon-account-patrol` 对我指定的店铺执行美国站只读巡检，只保存本地记录，不发送飞书；先确认店铺 ID 和市场，缺少必要信息时停止并告诉我。

## 效果预览

<div align="center">
  <a href="assets/patrol-report-example.png">
    <img src="assets/patrol-report-example.png" width="760" alt="脱敏的亚马逊六国账户巡检周报效果示例">
  </a>
</div>

> 这是历史六国巡检周报的脱敏效果示例，仅用于展示报告形态；当前 Skill 已扩展到九个市场，实际结果以本次巡检采集的证据为准。

## 安全边界

- 只复用目标紫鸟店铺已有会话和自动填充，不接收或保存 Amazon 密码、OTP。
- 不修改商品、价格、库存、广告、账号设置、Case、政策或通知。
- 不在仓库中写入店铺 ID、收件人、时区、个人路径或任何密钥。
- `amazon-patrol-output/`、日志、`.env` 和缓存已排除在 Git 提交之外。
- 页面原文、截图和巡检记录可能包含店铺敏感信息，应存放在用户批准的私有位置。

## 使用指引与技术资料

- [HTML 图文使用指引](blues19-amazon-account-patrol-使用指引.html)：图片已经内嵌，单独下载这个 HTML 也能完整显示；包含分页演示、主题切换和复制按钮。
- [环境安装与配置](references/setup.md)：Python、Node.js、`ziniao-cli`、授权和店铺可见性检查。
- [巡检执行流程](references/workflow.md)：状态机、证据标准和重试边界。
- [市场映射](references/marketplace-label-map.md)：9 个市场的公开标识。
- [页面选择器](references/element_selectors.md)：Seller Central 页面定位参考。
- [紫鸟 CLI 官方文档](https://open.ziniao.com/ziniaoCli)：CLI 安装、能力和官方业务案例。

安装官方紫鸟 Skills 后，还可以围绕员工授权、网页访问策略、差评响应、运营报告、Listing 维护、库存巡检和批量截图等场景制作独立 Skill。本仓库只内置 Amazon 账号健康与绩效通知的只读巡检，不代表已包含上述扩展功能。

## 项目结构

```text
blues19-amazon-account-patrol/
├─ SKILL.md
├─ agents/openai.yaml
├─ scripts/amazon_account_patrol.py
├─ references/
├─ tests/
├─ assets/
│  ├─ wechat-logo.jpg
│  └─ patrol-report-example.png
└─ blues19-amazon-account-patrol-使用指引.html
```

公众号：**拾玖说跨境AI**
