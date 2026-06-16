# TD Admin — 用户账号管理后台

独立的管理后台面板，用于管理 TD 旅游推荐平台的用户账号。

## 后端要求

需要先启动 TD 后端服务：
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## 默认管理员

- 用户名: `admin`
- 密码: `admin`

首次启动后务必修改密码。

## 部署方式

### 方式 1: 本地访问
直接双击 `index.html`，在浏览器中打开。

### 方式 2: 随主站一起部署
将 `index.html` 复制到主站的 `backend/static/admin.html`，通过 `http://localhost:8000/admin.html` 访问。

### 方式 3: 独立 GitHub Pages
1. 创建新的 GitHub 仓库
2. 上传 `index.html` 到仓库根目录
3. 开启 GitHub Pages (Settings → Pages → Source: main branch)
4. 部署后访问 `https://<your-username>.github.io/<repo-name>/`

### 方式 4: Vercel / Netlify 一键部署
将 `index.html` 拖入 Vercel 或 Netlify 即可。

## API 配置

后台默认连接 `http://localhost:8000/api`。

如需连接到其他后端，在浏览器控制台执行：
```js
localStorage.setItem('admin_api_base', 'https://your-server.com/api')
```
然后刷新页面。
