# 可选：简报 START 跳过重试（实验）

此项独立于汉化资源安装。默认不会安装或启用，也不包含用户本机的 RPCS3 配置。

适用 BLJM60012，PPU-706cbe20a07e41fae412eddce046cb3df7ba7b1d。通过 RPCS3 的补丁管理器导入 AC4_briefing_START_retry.yml，再启用 AC4 briefing START skip retry (experimental)，重新启动 AC4 生效。不要用此文件覆盖已有的 imported_patch.yml 或 patch_config.yml。若程序哈希不匹配，不会应用。

原生跳过会清空字幕，但影片尚未就绪时停止请求可能提前返回。本补丁仅在显式跳过标记存在且影片对象非空时重试原生停止函数；不绕过就绪检查，不强制场景结束，不改视频解码或渲染。

已做指令、分支、寄存器保护及延迟就绪模型检查，尚未完成游戏内验证。若出现异常，在补丁管理器取消勾选并重启游戏即可回退。它不是漏句或所有简报故障的已验证通用修复。
