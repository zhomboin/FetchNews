# TypeScript 开发规范

本文档定义当前前端 TypeScript 代码的命名与语法约束，基于 Google TypeScript Style Guide 的语法规范，并结合本项目实际约束收敛。

## 1. 命名规则

- 组件、类型、接口使用 `UpperCamelCase`
- 变量、函数、方法、参数、普通属性使用 `lowerCamelCase`
- 模块级不可变常量使用 `CONSTANT_CASE`
- 禁止使用 `_` 前缀或后缀命名

## 2. API 边界规则

- 前端内部状态、视图模型统一使用 `camelCase`
- 后端 `snake_case` 字段只能停留在 API 边界层
- `web/src/lib/api.ts` 负责将后端 DTO 映射为前端内部模型
- 页面组件和 feature 代码不得直接传播后端 `snake_case`

## 3. 组件书写规则

- 默认使用普通函数组件，不依赖 `React.FC`
- 导出的顶层组件在必要时补充有意义的 `/** JSDoc */`
- 不写重复类型信息的注释
- 不使用 `@override`

## 4. 常量与配置

- 模块级静态配置、查询 key、演示数据、平台枚举等统一使用 `CONSTANT_CASE`
- 尽量将常量定义收敛到模块顶部，避免在组件内部散落

## 5. 注释规则

- 注释必须提供额外信息，而不是重复代码表面含义
- 接口边界、映射逻辑和非显然的业务策略可以加短注释
- 不写“给变量赋值”这类无意义注释

## 6. 与仓库编码约定的关系

- TypeScript 文件统一使用 `UTF-8`、无 `BOM`
- 统一使用 `LF` 换行
- 遵循 [`.editorconfig`](/D:/Code/Project/FetchNews/.editorconfig) 与 [`.gitattributes`](/D:/Code/Project/FetchNews/.gitattributes)

## 7. 文档约束

- TypeScript 规范文档统一使用中文撰写
- 允许保留英文术语、类型名和代码示例，但解释必须使用中文