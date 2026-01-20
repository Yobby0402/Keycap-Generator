# Git 仓库设置说明

## 已完成的操作

1. ✅ 初始化 Git 仓库
2. ✅ 添加所有文件到 Git
3. ✅ 创建初始提交（dev0.1）
4. ✅ 添加远程仓库：https://github.com/Yobby0402/Keycap-Generator.git
5. ✅ 创建版本标签：dev0.1

## 推送代码

如果推送时提示需要认证，请使用以下方式之一：

### 方式1：使用 Personal Access Token（推荐）
1. 在 GitHub 上生成 Personal Access Token
2. 推送时使用 token 作为密码

### 方式2：使用 SSH（需要配置SSH密钥）
```bash
git remote set-url origin git@github.com:Yobby0402/Keycap-Generator.git
```

## 重命名文件夹

要将文件夹从 `KeyGenerator` 重命名为 `Keycap-Generator`：

1. **关闭所有正在使用该文件夹的程序**（包括 Cursor/VS Code）
2. 在文件管理器中，导航到 `F:\Code\`
3. 右键点击 `KeyGenerator` 文件夹
4. 选择"重命名"
5. 输入新名称：`Keycap-Generator`
6. 重新打开 Cursor/VS Code，打开新文件夹

**注意**：重命名后，Git 仓库仍然有效，因为 `.git` 文件夹在项目内部。

## 后续操作

推送代码后，可以：
- 在 GitHub 上查看代码
- 继续开发并提交新版本
- 创建新的标签和分支

## 常用 Git 命令

```bash
# 查看状态
git status

# 添加文件
git add .

# 提交更改
git commit -m "描述信息"

# 推送到远程
git push origin main

# 创建新标签
git tag -a v0.2 -m "Version 0.2"
git push origin v0.2
```
