# md2pdf

该项目继承至md2html，如有某些需要修正的地方，直接去隔壁寻找即可，已放弃，需要安装如下latex依赖

- [miktex](https://miktex.org/)

先将css-js的内容复制到html输出的位置，再使用 [md2html.py](md2html.py) 将md批量转化为html，最后使用 [create_index.py](create_index.py) 创建目录md，最后使用typora将其转化为单个index.html