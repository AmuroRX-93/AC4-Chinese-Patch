# 完整累计合并安装源码

本次交付为本地完整 ZIP，尚未创建新的 GitHub Release 附件。本目录记录已经验证的合并逻辑；不能单独下载本目录当作完整安装包。

以 2026-10-10 delta.5 三平台完整包为底座，复制本目录安装模块和 loadguard 子目录；loadguard/payload/eboot.bsdiff 使用 v2026.10.20-loadguard.1-rc1 中已发布的差分。原 base/font/finale/repair 差分载荷保持不变，复用底座的六套 Python 和三平台入口。生成最终包时必须重新计算全包校验清单及 SHA256SUMS。

合并器在原累计安装计划内追加最终 EBOOT 和 Normal 菜单，全部资源统一预检、统一提交及统一回退。合并安装验证.json 列明真实输入集、重复安装与回退、故障注入及未验证范围。

rc2 增加 update_resources.py 与 repair/install.py 接口：按内容识别更新目录资源，支持大小写、附属文件、嵌套菜单与已知程序；保留未知资源拒绝机制。更新目录兼容验证.json 是本次实测。修复未更改游戏内 EBOOT 差分载荷。
