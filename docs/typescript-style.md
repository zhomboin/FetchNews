# TypeScript 开发约束

本项目的前端 TypeScript 代码以 Google TypeScript Style Guide 的语法规范为基线，参考来源：

- [Google TypeScript Style Guide - Syntax](https://zh-google-styleguide.readthedocs.io/en/latest/google-typescript-styleguide/syntax.html)

当前项目采用的重点约束如下。

## 命名

- 类、组件、类型、接口使用 `UpperCamelCase`
- 变量、函数、方法、参数、普通属性使用 `lowerCamelCase`
- 模块级不可变常量使用 `CONSTANT_CASE`
- 不使用 `_` 作为标识符前缀或后缀
- 命名必须具备描述性，避免不清晰的缩写

## 前端模型与 API 边界

- React 组件和前端内部模型统一使用 `camelCase`
- 后端返回的 `snake_case` 字段只允许停留在 API 边界层
- `web/src/lib/api.ts` 负责 DTO 映射，页面组件不要直接消费后端原始字段名

## 注释与文档

- 导出的顶层类型、函数、组件，若职责不是一眼可知，补充有意义的 `/** JSDoc */`
- 注释只解释读者无法从名字和类型直接看出的信息
- 不写重复类型信息的 `@param` / `@return`
- 不使用 `@override`
- 实现细节说明使用普通行注释，面向调用方的说明使用 JSDoc

## 编码与字符

- TypeScript 文件统一使用 `UTF-8`、无 `BOM`
- 文本中允许直接使用可读的 Unicode 字符和中文文案
- 对不可见字符或转义字符，必须用转义形式并补说明注释

## React 项目内的具体执行规则

- 优先使用普通函数组件，不默认使用 `React.FC`
- 组件外的静态配置、演示数据、查询 key 和固定文案集合，按常量处理
- 页面组件尽量只处理展示和交互编排
- 请求拼装、响应映射、字段转换统一收口到 API 层

## 检查清单

修改 `web/` 代码时，至少自检以下事项：

1. 是否把新增标识符写成了符合场景的命名风格
2. 是否把后端 `snake_case` 泄漏到了组件内部
3. 是否新增了没有信息量的注释
4. 是否把应为常量的模块级值写成了普通变量命名
5. 是否运行了 `npm.cmd run build`