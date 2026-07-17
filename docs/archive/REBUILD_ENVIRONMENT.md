# Vault OS 环境重建快照

> 本快照于 2026-07-17 16:20 +08:00 在 C-1 容量清理的删除前建立。它只记录可安全公开的版本、锁文件哈希、脱敏依赖清单和重建前提；不记录绝对本机路径、私有索引 URL、Token、账号、密钥或实际配置值。

## 1. Python

| 项目 | 记录 |
| --- | --- |
| 当前虚拟环境解释器 | Python `3.12.10` |
| 当前虚拟环境 pip | pip `26.1`（Python 3.12） |
| `requirements.txt` SHA-256 | `0151A423E12EFA3F44E5B9654D70B9965488C08A0B0D46C4317CC9C5320E98DC` |
| 脱敏 `pip freeze --all` | 共 137 个可安全记录的 `包名==版本` 条目；未发现需要记录本地路径、Git URL、凭据或私有地址的未解析条目。 |

未来可按以下最小命令重建 Python 环境：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

当前环境的脱敏包名与版本如下；本列表不是锁文件，重建时应以 `requirements.txt` 为准。

```text
aiofiles==24.1.0
aiohappyeyeballs==2.6.1
aiohttp==3.13.5
aiosignal==1.4.0
altgraph==0.17.5
annotated-doc==0.0.4
annotated-types==0.7.0
anyio==4.13.0
attrs==26.1.0
babel==2.18.0
bcrypt==5.0.0
brotli==1.2.0
build==1.4.3
certifi==2026.2.25
cffi==2.0.0
charset-normalizer==3.4.7
chromadb==1.5.7
click==8.3.2
colorama==0.4.6
courlan==1.3.2
cryptography==46.0.7
dashscope==1.25.16
dateparser==1.4.0
ddgs==9.14.1
distro==1.9.0
durationpy==0.10
fastapi==0.135.3
feedparser==6.0.12
ffmpy==1.0.0
filelock==3.25.2
flatbuffers==25.12.19
frozenlist==1.8.0
fsspec==2026.3.0
googleapis-common-protos==1.74.0
gradio==6.11.0
gradio_client==2.4.0
greenlet==3.5.0
groovy==0.1.2
grpcio==1.80.0
h11==0.16.0
hf-gradio==0.3.0
hf-xet==1.4.3
htmldate==1.9.4
httpcore==1.0.9
httptools==0.7.1
httpx==0.28.1
huggingface_hub==1.9.2
idna==3.11
importlib_metadata==8.7.1
importlib_resources==7.1.0
Jinja2==3.1.6
jiter==0.13.0
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
jusText==3.0.2
kubernetes==35.0.0
lxml==6.0.2
lxml_html_clean==0.4.4
markdown-it-py==4.0.0
MarkupSafe==3.0.3
mdurl==0.1.2
mmh3==5.2.1
mpmath==1.3.0
multidict==6.7.1
numpy==2.4.4
oauthlib==3.3.1
onnxruntime==1.24.4
openai==2.31.0
opentelemetry-api==1.41.0
opentelemetry-exporter-otlp-proto-common==1.41.0
opentelemetry-exporter-otlp-proto-grpc==1.41.0
opentelemetry-proto==1.41.0
opentelemetry-sdk==1.41.0
opentelemetry-semantic-conventions==0.62b0
orjson==3.11.8
overrides==7.7.0
packaging==26.0
pandas==3.0.2
pefile==2024.8.26
pillow==12.2.0
pip==26.1
primp==1.2.3
propcache==0.4.1
protobuf==6.33.6
pybase64==1.4.3
pycparser==3.0
pydantic==2.12.5
pydantic-settings==2.13.1
pydantic_core==2.41.5
pydub==0.25.1
Pygments==2.20.0
pyinstaller==6.20.0
pyinstaller-hooks-contrib==2026.5
PyPika==0.51.1
pyproject_hooks==1.2.0
python-dateutil==2.9.0.post0
python-dotenv==1.2.2
python-frontmatter==1.1.0
python-multipart==0.0.24
pytz==2026.1.post1
pywin32-ctypes==0.2.3
PyYAML==6.0.3
referencing==0.37.0
regex==2026.4.4
requests==2.33.1
requests-oauthlib==2.0.0
rich==14.3.3
rpds-py==0.30.0
safehttpx==0.1.7
semantic-version==2.10.0
setuptools==82.0.1
sgmllib3k==1.0.0
shellingham==1.5.4
six==1.17.0
sniffio==1.3.1
SQLAlchemy==2.0.49
sqlmodel==0.0.38
starlette==1.0.0
sympy==1.14.0
tenacity==9.1.4
tld==0.13.2
tokenizers==0.22.2
tomlkit==0.13.3
tqdm==4.67.3
trafilatura==2.0.0
typer==0.24.1
typing-inspection==0.4.2
typing_extensions==4.15.0
tzdata==2026.1
tzlocal==5.3.1
urllib3==2.6.3
uvicorn==0.44.0
watchfiles==1.1.1
websocket-client==1.9.0
websockets==16.0
yarl==1.23.0
zipp==3.23.1
```

## 2. 前端

| 项目 | 记录 |
| --- | --- |
| Node.js | `v24.15.0` |
| npm | `11.12.1` |
| `chat-ui/package-lock.json` SHA-256 | `534C03BFAD59F0740301A3EC4DD6344743E3498EA68E0065BAA53B2A68EDA4B7` |

未来在 `chat-ui/` 下执行：

```powershell
npm ci
```

## 3. Tauri / Rust 与 Windows 打包

| 项目 | 记录 |
| --- | --- |
| rustc | `rustc 1.94.1 (e408947bf 2026-03-25)` |
| cargo | `cargo 1.94.1 (29ea6fb6a 2026-03-24)` |
| `chat-ui/src-tauri/Cargo.lock` SHA-256 | `C29919955D1DBF0831DF5C53AA9A35F866EF5ABF983DBA25199E1C7A60C87E56` |
| 当前 sidecar | `chat-ui/src-tauri/bin/vault_engine-x86_64-pc-windows-msvc.exe` 与 `chat-ui/src-tauri/bin/_internal/` 均存在；本批次未删除、读取或运行它们。 |

重新执行 Tauri Build 或 Windows 打包前，需要：

1. 先按本文件重建 Python 与前端依赖；Windows 打包脚本依赖 Python 虚拟环境中的 PyInstaller、`vault_engine.spec`、Node/npm 及已安装的前端依赖。
2. 准备 Rust MSVC 工具链、相应 Windows SDK 与 C++ 生成工具。当前只验证了 `rustc`、`cargo` 可用，未验证这些 Windows 构建前置条件。
3. 确认当前 sidecar 可以由 PyInstaller 重建后，再运行 `scripts/build-windows-release.ps1`；该脚本会重建 sidecar、复制到 `bin/`，随后在 `chat-ui/` 执行 `npm run tauri -- build`。
4. Tauri 配置当前只声明 `nsis` 目标。未在本批次运行 Tauri Build、Windows 打包、安装或卸载验证；任何生成的候选均不得据此描述为已发布或已验证。

## 4. C-1 清理前边界

清理前，四个已批准候选路径均存在。按文件元数据计算的逻辑文件大小为：`.venv/` 710,737,557 bytes、两个 `temp/` 候选分别为 244,499,176 bytes 和 325,192,443 bytes、`chat-ui/src-tauri/target/` 为 10,774,388,720 bytes，合计 12,054,817,896 bytes。该数字不是已释放空间，也不代表任何目录均可安全删除。

下列范围在快照时存在且仍受保护：`vault/`、`dist/vault/`、两个已列明的 Chroma 构建目录、全部 `build/smoke_vault_*`、`vault_seed/`、`chat-ui/src-tauri/bin/`、当前 sidecar、`bin/_internal/`、`chat-ui/node_modules/`、Dockerfile、依赖清单、业务代码、测试、`discard/`、Git 忽略规则和 README。

仓库内保留的 NSIS 源候选 SHA-256 为 `ACEEE0B63DEB9BBBE847E4DB548BEBE4EF3E6094A2930B1BAA987FC535E56162`，与既有私有归档标识 `VAULT-OS-PRIV-NSIS-001` 的记录一致。为避免把私有归档位置写入仓库，既有记录未保存其位置；因此本次不能仅凭该标识独立重新访问私有副本。该限制不应被解释为私有副本已再次验证。

## 5. 安全说明

- 本文不包含绝对本机路径、私有源地址、凭据、账号、密钥或配置值。
- `pip freeze` 输出仅在可安全解析为包名和版本时记录；不能安全脱敏的依赖必须写为待确认，不能回写原始来源。本次未出现该类条目。
- 本快照只提供重建依据，不授权删除运行时数据、当前 sidecar、私有发布资产或任何未列明范围。

## 6. C-1 删除后复核

2026-07-17，用户手动确认私有归档 `VAULT-OS-PRIV-NSIS-001` 存在且 SHA-256 匹配本文件记录的值，随后手动删除 `.venv/` 与 `chat-ui/src-tauri/target/`。只读复核确认两路径均不存在；`target/` 中的仓库内 NSIS 源候选也随之删除。

根据删除前已记录的文件元数据，移除的工作树逻辑文件容量为 11,485,126,277 bytes（10.696 GiB）：`.venv/` 为 710,737,557 bytes，`target/` 为 10,774,388,720 bytes。未采集文件系统可用空间的删除前基线，因此该数值不代表物理磁盘可用空间的精确增量。

当前 sidecar、`bin/_internal/`、`vault/`、`dist/vault/`、`vault_seed/`、列明的 Chroma/SQLite 构建目录、全部 `build/smoke_vault_*` 与两个 Windows staging 目录均保留。两个 staging 目录的运行时数据线索仍未读取，并已转入 OQ-DECOM-004；重建本地 Python 或 Tauri 环境时仍以本文件第 1 至 3 节为基线。
