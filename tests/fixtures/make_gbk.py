import io
import os


content = "姓名,年龄,分数,城市\n张三,25,88.5,北京\n李四,30,92.0,上海\n王五,28,79.3,北京\n赵六,35,95.1,广州\n"
out_path = os.path.join(os.path.dirname(__file__), "gbk_chinese.csv")
with open(out_path, "wb") as f:
    f.write(content.encode("gbk"))
print(f"wrote {out_path}")
