from pathlib import Path
from rembg import remove

BASE_DIR = Path(__file__).resolve().parent

input_path = BASE_DIR / "logo.png"
input_path2 = BASE_DIR / "CR.png"
input_path3 = BASE_DIR / "LBG.png"
output_path = BASE_DIR / "logor.png"
output_path2 = BASE_DIR / "CRr.png"
output_path3 = BASE_DIR / "LBGr.png"

with open(input_path, "rb") as input_file:
    input_data = input_file.read()

output_data = remove(input_data)

with open(output_path, "wb") as output_file:
    output_file.write(output_data)

print(f"Done: {output_path}")

with open(input_path2, "rb") as input_file2:
    input_data2 = input_file2.read()
output_data2 = remove(input_data2)
with open(output_path2, "wb") as output_file2:
    output_file2.write(output_data2)
print(f"Done: {output_path2}")

with open(input_path3, "rb") as input_file3:
    input_data3 = input_file3.read()
output_data3 = remove(input_data3)
with open(output_path3, "wb") as output_file3:
    output_file3.write(output_data3)
print(f"Done: {output_path3}")


