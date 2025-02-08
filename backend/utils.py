import io
import tempfile
from pathlib import Path
import pandas as pd
from xls2xlsx import XLS2XLSX
# from quadfeather.tiler import main
# from pyarrow import feather

async def convert_xls_to_xlsx(content: bytes) -> bytes:
    """
    Convert xls file to xlsx file using xls2xlsx.
    """   
    x2x = XLS2XLSX(io.BytesIO(content))
    workbook = x2x.to_xlsx()
    with io.BytesIO() as buffer:
        workbook.save(buffer)
        buffer.seek(0)
        return buffer.read()


async def save_file(file_name: str, content: str |bytes) -> str:
    folder_path = "ouput_tiles"
    file_path = f"{folder_path}/{file_name}"
    async with open(file_path,"w") as f:
        f.write(content)
        return file_path
    

# async def convert_dataframe_to_tiles(df: pd.DataFrame, output_dir: str, tile_size: int = 50000) -> str:
#     """
#     Convert a Pandas DataFrame into tiled data using quadfeather.
#     Return tiles_path - the saved titles folder path
#     """
#     tmp_path = "output_tiles"
#     tiles_path = Path(f"{tmp_path}/{output_dir}")
#     tiles_path.mkdir(parents=True, exist_ok=True)
 
#     with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_csv:
#         temp_csv_path = temp_csv.name
#         df.to_csv(temp_csv_path, index=False)
     
#     try:
#         main(
#             files=[temp_csv_path],
#             destination=str(tiles_path),
#             tile_size=tile_size,
#             extent = None
#         )
#         tb = feather.read_table(tmp_path / "tiles" / "0/0/0.feather")
#         manifest = feather.read_table(tmp_path / "tiles" / "manifest.feather")
#         assert manifest.num_rows == 1
#         assert manifest["min_ix"][0].as_py() == 0
#         assert manifest["max_ix"][0].as_py() == 3
#         # Should introduce a new 'ix' column.
#         for k in ["ix", "x", "y", "z"]:
#             assert k in tb.column_names
#         print(f"Successfully converted DataFrame to tiles in {output_dir}")
        
#     finally:
     
#         Path(temp_csv_path).unlink()
        
#         return tiles_path
