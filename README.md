# LittleNetTools
python project for class: sth of net tool(semi-finished product)
三个小功能

1. 端口扫描(有gui)
2. 目录匹配(半成品gui)
3. 简易netcat(无gui)

由于犯了菜鸟最常见的错误，在写程序前并没有规划好自己想写什么，代码结构很混乱导致自己debug都找不到哪里出错了，所以只能从头开始构建netcat，新开的坑里面规范了一下类和方法的编写，也学习了一些封装的用法，目前netcat能够实现命令执行，文件上传（大概），本来想给netcat写一个gui页面，但是时间实在是来不及了，就先鸽了……

## Portscangui

输入url和端口进行扫描



## Dirscangui

下载框架源码，提取出本地网站的目录结构，然后和在线的网站目录结构进行匹配（status为200则表示能够访问）



## Nc-try

建立连接后命令执行，文件长传和下载

> 由于是重构代码所以没有加参数解析。。



TodoList:

- 实现netcat的参数解析功能
- 实现netcat的gui页面
- 完善dirscan的gui页面
- 完善dirscan的服务识别功能
- 完善portscan功能，例如添加icmp探测功能
