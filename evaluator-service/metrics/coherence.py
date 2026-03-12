"""
Purpose: Evaluate logical progression between sequential documents.
Idea: doc1 → doc2, doc2 → doc3, doc3 → doc4
If adjacent documents are semantically related, coherence is high.
Coherence Metric = average_similarity_between_adjacent_documents
Formula: coherence = (sim(doc1,doc2) + sim(doc2,doc3) + ... + sim(docN-1,docN)) / (N-1)
"""

from embedding.similarity import semantic_similarity


def calculate_coherence(documents: list[str]) -> float:
    """
    For each adjacent document pair:
      Compute semantic similarity
    Return average similarity as coherence score.
    """
    # IF number_of_documents < 2 RETURN 0
    if len(documents) < 2:
        return 0.0

    # INITIALIZE empty list similarity_scores
    similarity_scores: list[float] = []

    # FOR i from 0 to length(documents)-2
    for i in range(len(documents) - 1):
        current_doc = documents[i]
        next_doc = documents[i + 1]

        # similarity = semantic_similarity(current_doc, next_doc)
        similarity = semantic_similarity(current_doc, next_doc)
        similarity_scores.append(similarity)

    # coherence_score = average(similarity_scores)
    coherence_score = sum(similarity_scores) / len(similarity_scores)

    return round(coherence_score, 4)
