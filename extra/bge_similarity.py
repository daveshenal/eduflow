import torch
from sentence_transformers import SentenceTransformer
import time

# # Test text
# text_samples = [
#     "REST is an architectural style for web services.",
#     "HTTP methods include GET, POST, PUT, and DELETE.",
#     "Endpoints represent resources in a RESTful API.",
# ] * 50  # 150 samples

# # Load model
# device = "cuda" if torch.cuda.is_available() else "cpu"
# print(f"Using device: {device}")

# model = SentenceTransformer('BAAI/bge-large-en-v1.5', device=device)

# # Encode
# start = time.time()
# embeddings = model.encode(text_samples, batch_size=8, show_progress_bar=True)
# elapsed = time.time() - start

# # Results
# print(f"\nSamples: {len(embeddings)}")
# print(f"Dimensions: {embeddings.shape[1]}")
# print(f"Time: {elapsed:.2f}s")
# print(f"Speed: {len(embeddings)/elapsed:.1f} samples/sec")

if torch.cuda.is_available():
    print(f"GPU memory: {torch.cuda.memory_allocated() / 1024**2:.0f} MB")