# Envocab

英语词汇学习与管理工具，支持分组词库、英汉搜索、词典查询、词条编辑和随机自测。词库涵盖初中、高中、四六级、考研、雅思及 COCA。

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
