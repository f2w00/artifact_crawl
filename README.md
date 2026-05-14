# 数据
csv格式为:

- ID,名称,年代,编号,图片地址

	- 其中**ID**: 指向output/nmc/images中的图片, 图片命名为{ID}.jpg, ID是跨文件递增的,ID在images中唯一
	- 名称: 为文物名称, 不唯一
    - 年代: 为文物年代, 字符串并非date格式, 不唯一
	- 编号: 为博物馆编号, 唯一
	- 图片地址: 是http url, 可以直接访问/下载, 建议检查images中图片是否存在, 如无, 下载

一共9个csv文件, 文件命名为nmc_{page}.csv

page从1开始, 每个page/csv文件对应120000条数据, 不要依赖这个数字, 并不100%确定有120000条数据

检查images中图片是否存在, 如无, 按照图片地址下载到images中

# 脚本
- nmc.py 下载nmc数据
- clean.py 根据脚本内的参数删除output/nmc/images下id大于参数的图片
- ensure.py 下载缺失的图片
- count.py 统计nmc数据量