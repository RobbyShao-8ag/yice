# 贡献指南

感谢你愿意为易策（yice）贡献力量！🎋

## 🤝 如何贡献

### 报告问题
- 使用 [Issue模板](https://github.com/RobbyShao-8ag/yice/issues/new/choose) 创建问题
- 描述清晰，提供环境信息、复现步骤
- 搜索是否已有类似问题，避免重复

### 提出功能建议
- 同样使用 [Issue模板](https://github.com/RobbyShao-8ag/yice/issues/new/choose)
- 说明使用场景和价值
- 可以附上参考资料或草图

### 代码贡献

#### 开发环境准备

**CLI版本（开箱即用，无需安装依赖）：**
```bash
git clone https://github.com/RobbyShao-8ag/yice.git
cd yice
python main.py
# 直接运行，无需任何安装！
```

**Web版本（需要安装后端依赖）：**
```bash
cd yice/web/backend
pip install -r requirements.txt
python main.py
```

#### 开发流程

1. **Fork 仓库** → 在你的GitHub账户下创建副本
2. **创建分支** → 起一个有意义的分支名
   ```bash
   git checkout -b feature/your-feature-name
   # 或修复bug
   git checkout -b fix/issue-number-brief-description
   ```
3. **编写代码** → 遵循项目现有的代码风格
4. **测试** → 确保改动有测试覆盖
   ```bash
   # 确保安装了pytest
   pip install pytest

   # 运行所有测试
   pytest tests/

   # 只运行核心模块测试
   pytest tests/core/ tests/agents/

   # 带覆盖率报告
   pytest tests/ --cov=. --cov-report=term-missing
   ```
5. **提交** → 提交信息要清晰描述改动
   ```bash
   git commit -m "feat: 添加xxx功能"
   # 提交类型: feat | fix | docs | style | refactor | test | chore
   ```
6. **推送并提PR** → 将分支推送到你的Fork，然后创建Pull Request

#### Commit 规范

```
<type>: <subject>

可选的详细描述
```

**Type 类型：**
- `feat` - 新功能
- `fix` - Bug修复
- `docs` - 文档更新
- `style` - 代码格式（不影响功能）
- `refactor` - 重构
- `test` - 测试相关
- `chore` - 构建/工具相关

## 📐 代码规范

### Python
- 遵循 PEP 8
- 使用有意义的变量和函数命名
- 公共函数添加 docstring
- 类型注解尽量完整

### 核心设计原则
- 保持模块职责单一
- 尊重现有的架构设计（参考 `core/` 和 `agents/` 目录）
- 周易相关的逻辑请保持学术准确性，参考 `docs/` 中的参考文献

## 🧪 测试

所有新增功能**必须**包含测试：

```bash
# 运行所有测试
pytest tests/

# 只运行核心模块测试
pytest tests/core/ tests/agents/

# 带覆盖率报告
pytest tests/ --cov=. --cov-report=term-missing
```

测试文件在 `tests/` 目录下，使用 **pytest** 框架。

## 📄 文档

- 如果是新增功能，请更新 README.md 对应部分
- 如果涉及API变更，需要更新 docs/ 目录下的相关文档
- 中文文档为主，英文可作为补充

## 🔍 Code Review

收到PR后，维护者会在3个工作日内回复。

PR被合并前需要满足：
- [ ] 所有测试通过
- [ ] 代码审查通过
- [ ] 文档已更新（如需要）
- [ ] 无冲突分支

## 📜 许可证

本项目采用 **MIT License** 开源许可证。

贡献的代码同样遵循 MIT License。

---

**一起让易策变得更好！** 🐉
