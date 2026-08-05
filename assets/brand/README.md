# Journey 品牌资产

本目录保存从旧微信小程序提取、且与 Taro 源码解耦的品牌资产。文件保持原始字节不变，仅使用更明确的名称。

| 文件 | 原始文件 | 用途 |
|---|---|---|
| `journey-leaf-home.png` | `src/assets/home.png` | 叶子角色日常/首页状态 |
| `journey-leaf-food.png` | `src/assets/eat1.png` | 叶子角色饮食状态 |
| `journey-leaf-activity.png` | `src/assets/sport1.png` | 叶子角色运动状态 |
| `journey-sticker-logo.svg` | `src/assets/sticker-logo.svg` | 96×96 Journey 标识候选；旧页面未实际引用 |

完整尺寸、哈希、引用和来源状态见
[`docs/product/LEGACY_ASSET_INVENTORY.md`](../../docs/product/LEGACY_ASSET_INVENTORY.md)。

## 使用约束

- 阶段 2 不重新设计或压缩这些文件。
- 在公开发布前必须由项目所有者确认原创/授权来源；Git 历史只能证明文件何时进入仓库，不能替代版权证明。
- 新客户端应通过资产映射或组件封装引用，不依赖旧 `src/assets/index.js`。
- 原始 PNG 含透明通道，React Native 中应避免依赖图片内部绿色背景与页面背景完全一致。
