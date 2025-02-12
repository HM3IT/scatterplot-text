import io
import os
import boto3
import json
from typing import Annotated
from dotenv import load_dotenv
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.cluster import HDBSCAN

from sklearn.manifold import TSNE
from umap import UMAP
from transformers import AutoModel, AutoTokenizer

from litestar import Litestar, get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin, ScalarRenderPlugin
from litestar.config.cors import CORSConfig

from utils import convert_xls_to_xlsx, generate_topic_with_bedrock
from litestar.logging import LoggingConfig

load_dotenv()

cors_config = CORSConfig(allow_origins=["*"], allow_headers=["*"], allow_methods=["*"]) 
tokenizer = AutoTokenizer.from_pretrained("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
model = AutoModel.from_pretrained("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)


bedrock_model = os.environ["BEDROCK_MODEL_NAME"]
 
logging_config = LoggingConfig(
    root={"level": "INFO", "handlers": ["queue_listener"]},
    formatters={
        "standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
    },
    log_exceptions="always",
)

@get("/")
async def index() -> str:
    return "Hello, world!"

@post("api/graphs/generate")
async def generate_graph(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> dict[str, int]:
    """
    Generate a json output of the graph with clusters
    Cluster with -1 is considered an outlier or not part of any 'dense' cluster.
    """
    
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
        print("reached csv reader")
        df = pd.read_csv(io.BytesIO(content), header=0, na_filter=False, on_bad_lines='skip')
    else:
        raise ValueError("Unsupported file type")

    if "COMPLAINT_SUMMARY" not in df.columns:
        raise ValueError("'COMPLAINT_SUMMARY' column is missing in the uploaded file")

    boto3_client = boto3.client('bedrock-runtime', 
    region_name=os.environ["AWS_REGION"],
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"]
    )

    texts = df["COMPLAINT_SUMMARY"].astype(str).tolist()
    batch_size = 100 
    embeddings_3d_batches = []

    min_cluster_size = 10
    min_dist = 0.2
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        encoded_input = tokenizer(batch_texts, padding=True, truncation=True, max_length=8192, return_tensors='pt')
        with torch.no_grad():
            model_output = model(**encoded_input)
        embeddings = await mean_pooling(model_output, encoded_input["attention_mask"])
        embeddings = F.normalize(embeddings, p=3, dim=1)
        embeddings_hd = embeddings.cpu().numpy()
     
        # tsne = TSNE(n_components=3, random_state=42, perplexity=3, n_iter=1000)
        # embeddings_3d_batch = tsne.fit_transform(embeddings_hd)
        umap = UMAP(n_components=3, random_state=42, n_neighbors=30, min_dist=min_dist)
        embeddings_3d = umap.fit_transform(embeddings_hd)
        embeddings_3d_batches.append(embeddings_3d)
 
    embeddings_3d = np.vstack(embeddings_3d_batches)
    df["x"] = embeddings_3d[:, 0]
    df["y"] = embeddings_3d[:, 1]
    df["z"] = embeddings_3d[:, 2]

    clusterer = HDBSCAN(min_cluster_size=min_cluster_size, min_samples=5, cluster_selection_epsilon=0.5)
    cluster_labels = clusterer.fit_predict(embeddings_3d)
    df["cluster"] = cluster_labels

    # # Exclude noise (-1) if desired as -1 are outlier points
    valid_clusters = df[df["cluster"] != -1]["cluster"]
    if not valid_clusters.empty:
        # Get cluster counts and sort clusters in ascending order by size.
        cluster_counts = valid_clusters.value_counts().sort_values()
        sorted_clusters = cluster_counts.index.tolist()
    else:
        sorted_clusters = [-1]   
    cluster_topics = {}
    for cl in sorted_clusters:
        cluster_texts = df.loc[df["cluster"] == cl, "COMPLAINT_SUMMARY"].tolist()
        aggregated_text = " ".join(cluster_texts)
        print(f"Getting topic for {cl}")
        topic = generate_topic_with_bedrock(boto3_client, bedrock_model, aggregated_text)
        cluster_topics[cl] = topic
 
    df["topic"] = df["cluster"].apply(lambda cl: cluster_topics.get(cl, "Noise"))

    # sort by cluster size (ascending).
    df["cluster_order"] = df["cluster"].apply(lambda cl: sorted_clusters.index(cl) if cl in sorted_clusters else -1)
    df = df.sort_values("cluster_order").drop(columns=["cluster_order"])
 
    fields_to_include = [
        "COMPLAINT_ID", "CONTRACT_ID", "PARENT_ORGANIZATION", "REGION_RESPONSIBLE",
        "CATEGORY", "SUBCATEGORY", "SUBCATEGORY_OTHER", "COMPLAINT_SUMMARY",
        "UPDATED_DATE", "CASEWORK", "COMMENT_TEXT", "COMPLAINANT_TYPE", "STATE",
        "x", "y", "z", "cluster", "topic"
    ]
    data_json = df[fields_to_include].to_json(orient="records")
    
    with open(f"umap_c_size{min_cluster_size}_&_min_dist_{min_dist}.json", "w") as f:
        json.dump(json.loads(data_json), f, indent=4)
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
    logging_config=logging_config
)