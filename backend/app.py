import io
from typing import Annotated

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

# from sklearn.manifold import TSNE
from umap import UMAP
from transformers import AutoModel, AutoTokenizer

from litestar import Litestar, get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin, ScalarRenderPlugin
from litestar.config.cors import CORSConfig

from utils import convert_xls_to_xlsx

cors_config = CORSConfig(allow_origins=["*"], allow_headers=["*"], allow_methods=["*"]) 
tokenizer = AutoTokenizer.from_pretrained("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
model = AutoModel.from_pretrained("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)


@get("/")
async def index() -> str:
    return "Hello, world!"


@post("api/graphs/generate")
async def generate_graph(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> dict[str, int]:
    content = await data.read()
    content_type = data.content_type

    if content_type in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
        "application/vnd.ms-excel",  # xls
    ):
        if content_type == "application/vnd.ms-excel":
            content = await convert_xls_to_xlsx(content)
        
        df = pd.read_excel(io.BytesIO(content), header=0, na_filter=False)
    elif content_type == "text/csv":
        df = pd.read_csv(io.BytesIO(content), header=0, na_filter=False)
    else:
        raise ValueError("Unsupported file type")

    if "COMPLAINT_SUMMARY" not in df.columns:
        raise ValueError("'COMPLAINT_SUMMARY' column is missing in the uploaded file")

    # Create a list of all the complaint summaries
    texts = df["COMPLAINT_SUMMARY"].astype(str).tolist()
    # Process 100 rows at a time
    batch_size = 100 
    embeddings_2d = []  

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
 
        encoded_input = tokenizer(batch_texts, padding=True, truncation=True, max_length=8192, return_tensors='pt')

        with torch.no_grad():
            model_output = model(**encoded_input)
 
        embeddings = await mean_pooling(model_output, encoded_input["attention_mask"])
        embeddings = F.normalize(embeddings, p=3, dim=1)
        embeddings_hd = embeddings.cpu().numpy()
     
        umap = UMAP(n_components=3, random_state=42, n_neighbors=15, min_dist=0.1)
        embeddings_2d_batch = umap.fit_transform(embeddings_hd)

  
        embeddings_2d.append(embeddings_2d_batch)
 
    embeddings_2d = np.vstack(embeddings_2d)
    df["x"] = embeddings_2d[:, 0]
    df["y"] = embeddings_2d[:, 1]
    df["z"] = embeddings_2d[:, 2]
 
    fields_to_include = [
        "COMPLAINT_ID", "CONTRACT_ID", "PARENT_ORGANIZATION", "REGION_RESPONSIBLE",
        "CATEGORY", "SUBCATEGORY", "SUBCATEGORY_OTHER", "COMPLAINT_SUMMARY",
        "UPDATED_DATE", "CASEWORK", "COMMENT_TEXT", "COMPLAINANT_TYPE", "STATE",
        "x", "y", "z"
    ]

 
    data_json = df[fields_to_include].to_json(orient="records")

    return data_json
        

async def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)



openapi_config = OpenAPIConfig(
    title="complaint-plotter",
    version="0.0.1",
    use_handler_docstrings=True,
    render_plugins=[
        ScalarRenderPlugin(),
        SwaggerRenderPlugin()
    ],
)

app = Litestar(
    route_handlers=[index, generate_graph],
    openapi_config=openapi_config,
    cors_config = cors_config,
    
)