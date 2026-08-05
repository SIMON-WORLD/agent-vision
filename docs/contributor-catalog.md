# 已验证的共同作者（Co-Author）目录

本目录只保留**实测能进入 Contributors 页面**的身份（A 组 + C 组）。
曾经测试的 B 组（Gemini/Copilot 的 noreply 邮箱、ChatGPT、Aider、Cline、Cursor、Windsurf）
已实测不会进入页面，故从本目录移除。

> 快速安装：`bash <(curl -fsSL https://raw.githubusercontent.com/academic-door/github-multiagent-contributor/main/scripts/fetch-kit.sh)`
>
> 透明披露：共同作者尾注只用于署名归因，不代表对应工具真实参与了每一个提交；
> 本仓库把它当作“归因记录”功能使用，与 `activity/agent-checkins.csv` 配套。

## A. 已验证计入页面的 AI 身份

| ID | 展示名 | 尾注格式 | 工具本身免费？ | 备注 |
|---|---|---|---|---|
| codex | Codex | `Codex <noreply@openai.com>` | 有免费额度 | OpenAI 官方 no-reply 邮箱 |
| claude | Claude | `Claude <noreply@anthropic.com>` | 有免费额度 | Anthropic 官方 no-reply 邮箱 |

## C. 真实 GitHub Bot 账号（必然进入 Contributors）

与 `dependabot[bot]`、`github-actions[bot]` 一样是真实 GitHub 账号，邮箱格式
`{id}+{login}@users.noreply.github.com`，解析是确定性的（已验证 6/6 起步，已扩展到 33 个）：

| ID | 展示名 | 尾注格式 | 说明 |
|---|---|---|---|
| gemini-code-assist | gemini-code-assist[bot] | `gemini-code-assist[bot] <176961590+gemini-code-assist[bot]@users.noreply.github.com>` | Google Gemini Code Assist 官方 bot |
| renovate | renovate[bot] | `renovate[bot] <29139614+renovate[bot]@users.noreply.github.com>` | Mend Renovate 依赖机器人 |
| pre-commit-ci | pre-commit-ci[bot] | `pre-commit-ci[bot] <66853113+pre-commit-ci[bot]@users.noreply.github.com>` | pre-commit.ci 自动修复 |
| snyk | snyk-bot | `snyk-bot <19733683+snyk-bot@users.noreply.github.com>` | Snyk 安全修复 |
| all-contributors | allcontributors[bot] | `allcontributors[bot] <46447321+allcontributors[bot]@users.noreply.github.com>` | all-contributors 名单机器人 |
| copilot-bot | copilot[bot] | `copilot[bot] <167198135+copilot[bot]@users.noreply.github.com>` | GitHub Copilot 官方 bot 账号 |
| claude-bot | claude[bot] | `claude[bot] <209825114+claude[bot]@users.noreply.github.com>` | Anthropic Claude 官方 bot 账号 |
| cursor-bot | cursor[bot] | `cursor[bot] <206951365+cursor[bot]@users.noreply.github.com>` | Cursor AI 官方 bot 账号 |
| qodo-merge | qodo-merge[bot] | `qodo-merge[bot] <185363710+qodo-merge[bot]@users.noreply.github.com>` | Qodo Merge（PR-Agent）AI 审查/合并 bot |
| mergify | mergify[bot] | `mergify[bot] <37929162+mergify[bot]@users.noreply.github.com>` | Mergify 合并队列 |
| kodiakhq | kodiakhq[bot] | `kodiakhq[bot] <49736102+kodiakhq[bot]@users.noreply.github.com>` | Kodiak 合并队列 |
| github-merge-queue | github-merge-queue[bot] | `github-merge-queue[bot] <118344674+github-merge-queue[bot]@users.noreply.github.com>` | GitHub Merge Queue |
| scala-steward | scala-steward | `scala-steward <43047562+scala-steward@users.noreply.github.com>` | Scala 依赖更新机器人 |
| pyup | pyup-bot | `pyup-bot <16239342+pyup-bot@users.noreply.github.com>` | Python 依赖更新机器人 |
| mend | mend[bot] | `mend[bot] <241224340+mend[bot]@users.noreply.github.com>` | Mend 安全扫描 bot |
| greenkeeper | greenkeeper[bot] | `greenkeeper[bot] <23040076+greenkeeper[bot]@users.noreply.github.com>` | npm 依赖 bot（已停用） |
| dependabot-preview | dependabot-preview[bot] | `dependabot-preview[bot] <27856297+dependabot-preview[bot]@users.noreply.github.com>` | Dependabot 旧版 bot（已停用） |
| semantic-release | semantic-release-bot | `semantic-release-bot <32174276+semantic-release-bot@users.noreply.github.com>` | semantic-release 发布/提交 bot |
| codecov | codecov[bot] | `codecov[bot] <22429695+codecov[bot]@users.noreply.github.com>` | Codecov 覆盖率 bot |
| github-classroom | github-classroom[bot] | `github-classroom[bot] <66690702+github-classroom[bot]@users.noreply.github.com>` | GitHub Classroom |
| github-learning-lab | github-learning-lab[bot] | `github-learning-lab[bot] <37936606+github-learning-lab[bot]@users.noreply.github.com>` | GitHub Learning Lab |
| first-timers | first-timers[bot] | `first-timers[bot] <31459394+first-timers[bot]@users.noreply.github.com>` | first-timers 引导 bot |
| request-info | request-info[bot] | `request-info[bot] <30733101+request-info[bot]@users.noreply.github.com>` | request-info 信息补充 bot |
| stale | stale[bot] | `stale[bot] <26384082+stale[bot]@users.noreply.github.com>` | stale 过期关闭 bot |
| todo | todo[bot] | `todo[bot] <32347756+todo[bot]@users.noreply.github.com>` | todo 转 Issue bot |
| welcome | welcome[bot] | `welcome[bot] <30606887+welcome[bot]@users.noreply.github.com>` | welcome 欢迎 bot |
| wip | wip[bot] | `wip[bot] <29805525+wip[bot]@users.noreply.github.com>` | WIP 状态检查 bot |
| hound | hound[bot] | `hound[bot] <30008653+hound[bot]@users.noreply.github.com>` | Hound 代码风格审查 bot |
| stickler-ci | stickler-ci[bot] | `stickler-ci[bot] <41810448+stickler-ci[bot]@users.noreply.github.com>` | Stickler CI 风格检查 bot |
| release-drafter | release-drafter[bot] | `release-drafter[bot] <40829082+release-drafter[bot]@users.noreply.github.com>` | Release Drafter 发布草稿 bot |
| pypi | pypi[bot] | `pypi[bot] <253595658+pypi[bot]@users.noreply.github.com>` | PyPI 官方 bot |
| npm | npm[bot] | `npm[bot] <38296568+npm[bot]@users.noreply.github.com>` | npm 官方 bot |
| octokit | octokit[bot] | `octokit[bot] <171388558+octokit[bot]@users.noreply.github.com>` | GitHub 官方 Octokit bot |

说明：
- 带 `[bot]` 的名字可以放进 `AGENT_CHECKIN_AUTHORS`（工作流正则已支持方括号），
  但默认清单只放 A 组，C 组按需用 `--bots` 单独加。
- 部分 C 组账号（如 stale/wip/request-info 等）以评论/检查为主，仍保留在目录用于机制演示。

## 如何把身份加到一个提交

```bash
# 列出全部身份
python scripts/build_contributors.py --list

# 选择部分身份（逗号分隔 ID，可混选 A/C 组）
python scripts/build_contributors.py --tools codex,renovate,snyk

# 只选真实 Bot 账号（C 组，进入页面最稳）
python scripts/build_contributors.py --bots

# 选择全部（A+C）
python scripts/build_contributors.py --all

# 自助：自动建分支 + 提交 + 尾注（推荐给 Agent）
python scripts/build_contributors.py --apply --tools codex,renovate,snyk

# 直接生成带尾注的完整提交信息
python scripts/build_contributors.py --bots --commit-message "feat: example"
```

把生成的 `Co-Authored-By:` 行追加到 commit message 末尾再提交即可。
提交进入默认分支（直接 push 或 squash 合并均可保留尾注）后，刷新 Contributors 页面验证。

## 如何移除身份

- **停止再新增**：`python scripts/build_contributors.py --remove --tools renovate`
  会同时从本目录和 `build_contributors.py` 删除该身份；并把仓库变量 `AGENT_CHECKIN_AUTHORS`
  里对应的身份删掉（若 check-in 在用）。
- **历史提交仍计入页面**：`--remove` 只影响未来；想从 Contributors 页面抹去历史只能重写
  默认分支历史（force-push，高风险，不推荐）。
- **验证**：`python scripts/build_contributors.py --check --tools renovate` 应显示 ABSENT。

## 迁移到其他仓库（三步）

1. 一键安装套件（见顶部命令），或手动复制本目录的 `docs/contributor-catalog.md` 与 `scripts/build_contributors.py` 到目标仓库。
2. 用 `build_contributors.py` 选择要添加的身份（A 组或 C 组），把尾注写进提交信息并合并进默认分支。
3. 刷新目标仓库 Contributors 页面，核对出现哪些身份。

### 可选：让每日 check-in 自动携带选中的身份

参考 `.github/workflows/scheduled-agent-checkin.yml`：
- 默认会携带 Codex、Claude 与维护者（可设置仓库变量 `AGENT_CHECKIN_AUTHORS` 覆盖）；
- 开启方式：设置仓库变量 `AGENT_CHECKIN_ENABLED=true`，然后手动运行一次该工作流。
