# Envocab

英语词汇学习与管理工具，支持分组词库、英汉搜索、词典查询、词条编辑和随机自测。词库涵盖初中、高中、四六级、考研、雅思及 COCA。

Check 页面每次出现单词时自动播放美式发音，也可点击喇叭重播。首次自动播放若被浏览器拦截，点击一次喇叭后继续使用。音频通过后端 `/api/pronunciation?term=hello` 从有道词典获取，无需 API Key；服务端提供有界内存缓存，浏览器缓存一天。此功能需要后端能访问 `dict.youdao.com`，依赖其网页发音接口的可用性。

登录后，Check 使用 [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs) 的 FSRS-6 算法安排复习，目标记忆保持率为 90%。三个按钮对应 `NO → Again（忘记）`、`HARD → Hard（正确但回忆困难）`、`YES → Good（正确回忆）`，每次回答更新记忆稳定性、难度和下次复习时间，并保存独立历史记录。初学步骤为 1 分钟和 10 分钟，遗忘后的重学步骤为 10 分钟；长期复习间隔由算法计算，不再使用分数加减或加权随机。

Check 优先展示到期的学习／重学词，再展示到期复习词；没有到期词时学习新词。全部完成时显示下次复习时间并在到期后自动刷新，不提前反复展示未到期词。未登录时仍提供随机浏览，但不能保存学习记录。

0～5 分仅作为熟练等级展示，不参与 FSRS 计算：忘记为 0 分，学习／重学阶段为 1 分；进入长期复习后，记忆稳定性不足 1 天、1～3 天、3～7 天、7～30 天、30 天及以上分别显示 1～5 分。5 分仍会继续复习。词库进度仍为熟练等级的加权汇总，并非实际记忆概率。当前使用默认模型参数，已保存的历史可供后续个性化优化，本版尚未自动训练个人参数。

升级需执行 `cd server && uv sync --locked && uv run alembic upgrade head`。迁移保留旧分数和答题次数；因旧数据没有逐次答题历史，旧词会作为待复习词，在下次真实回答时初始化 FSRS，并更新展示等级，不伪造历史。学习状态和历史按用户隔离，同一单词跨词库共享。

## 技术栈

- 前端：Next.js、React、TypeScript、Tailwind CSS、shadcn/ui
- 后端：FastAPI、SQLAlchemy、PostgreSQL，使用 Alembic 管理迁移
- 目录：`ui/` 前端，`server/` 后端，`rawlist/` 词表及来源说明

## 本地运行

需要 Node.js 24+、npm、uv、Python 3.15 和 PostgreSQL 18。

```sh
createdb envocab  # 仅首次创建数据库时执行
make setup
make dev
```

打开 <http://localhost:3000>。后端默认监听 `127.0.0.1:8000`，前端代理 `/api/*` 请求。

`make setup` 安装锁定依赖、创建缺失的环境配置、下载词典并执行数据库迁移；首次下载词典需要联网，词表导入需另行执行。

## 配置与命令

- `server/.env`：`DATABASE_URL`，默认 `postgresql+psycopg:///envocab`
- `ui/.env.local`：`API_URL`，默认 `http://127.0.0.1:8000`
- `make check`：运行代码检查、测试、类型检查和生产构建
- `make migrate`：应用数据库迁移
- `make dictionary`：下载并重建本地词典索引
- `make ui` / `make server`：单独启动前端或后端

词典基于 [ECDICT](https://github.com/skywind3000/ECDICT)，许可证见 [ECDICT.txt](server/licenses/ECDICT.txt)。本地数据库、环境配置和构建产物不提交到 Git。
