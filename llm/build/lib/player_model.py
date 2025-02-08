import copy
import numpy as np
from sklearn.decomposition import PCA
import torch
import datetime
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class PlayerModel:
    def __init__(self):
        self.history = []  
        self.sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        self.role_sentiment_counts = {
            "player": {"positive": 0, "neutral": 0, "negative": 0},
            "llm": {"positive": 0, "neutral": 0, "negative": 0}
        }
        self.twitter_tokenizer = AutoTokenizer.from_pretrained("cardiffnlp/twitter-roberta-base-sentiment")
        self.twitter_model = AutoModelForSequenceClassification.from_pretrained("cardiffnlp/twitter-roberta-base-sentiment")
    
    
    def get_sentiment_twitter(self, text):
        tokens = self.twitter_tokenizer(text, return_tensors="pt")
        outputs = self.twitter_model(**tokens)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1).tolist()[0]
        labels = ["negative", "neutral", "positive"]
        predicted_label = labels[probs.index(max(probs))]
        compound = probs[2] - probs[0]
        score_dict = {"neg": probs[0], "neu": probs[1], "pos": probs[2], "compound": compound}
        return predicted_label, score_dict
    
    def print_chunk_distances(self, embedding, chunked_embeddings):
        """Print the Euclidean distance between the main embedding and each chunk."""
        for idx, chunk in enumerate(chunked_embeddings):
            distance = np.linalg.norm(embedding - chunk)
            print(f"Distance between main embedding and chunk {idx}: {distance:.4f}")
    
    def update(self, embedding, chunked_embeddings, message, role):
        predicted_label, scores = self.get_sentiment_twitter(message)
        compound = scores["compound"]
        if compound >= 0.05:
            sentiment = "positive"
        elif compound <= -0.05:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        self.sentiment_counts[sentiment] += 1
        if role in self.role_sentiment_counts:
            self.role_sentiment_counts[role][sentiment] += 1
        else:
            self.role_sentiment_counts[role] = {"positive": 0, "neutral": 0, "negative": 0}
            self.role_sentiment_counts[role][sentiment] = 1
        order = len(self.history) + 1
        timestamp = datetime.datetime.now().isoformat()
        
        # Call the helper to print distances between main embedding and each chunk.
        if chunked_embeddings:
            print(order)
            self.print_chunk_distances(embedding, chunked_embeddings)
        
        self.history.append({
            "order": order,
            "timestamp": timestamp,
            "role": role,
            "message": message,
            "embedding": embedding,
            "chunked_embeddings": chunked_embeddings,
            "sentiment": sentiment,
            "sentiment_scores": scores,
            "role_sentiment_counts": self.role_sentiment_counts[role],
            "overall_sentiment_counts": self.sentiment_counts
        })

            
    def get_history_for_visualization(self):
        import copy
        if not self.history:
            return []
        # Make a deep copy of the history so that the stored high-dimensional embeddings remain unchanged.
        reduced_history = copy.deepcopy(self.history)
        
        def reduce_entry_embeddings(main_embedding, chunked_embeddings, n_components=3):
            """
            For a single history entry, combine the main embedding and its chunked embeddings,
            then compute PCA on the union. Return the reduced main embedding and the reduced chunk embeddings.
            """
            combined = [main_embedding]
            if chunked_embeddings is not None:
                combined.extend(chunked_embeddings)
            combined = np.array(combined)
            effective_n_components = min(n_components, combined.shape[0])
            if combined.shape[0] == 1:
                reduced = combined[:, :n_components]
            else:
                pca = PCA(n_components=effective_n_components)
                reduced = pca.fit_transform(combined)
                if reduced.shape[1] < n_components:
                    pad_width = n_components - reduced.shape[1]
                    reduced = np.hstack([reduced, np.zeros((reduced.shape[0], pad_width))])
            # The first row is the reduced main embedding; remaining rows (if any) are reduced chunk embeddings.
            new_main = reduced[0]
            new_chunks = reduced[1:] if reduced.shape[0] > 1 else None
            return new_main, new_chunks

        # For each history entry, reduce the main and chunked embeddings on a per-message basis.
        for entry in reduced_history:
            main_emb = entry["embedding"]
            chunked_embs = entry.get("chunked_embeddings", None)
            new_main, new_chunks = reduce_entry_embeddings(main_emb, chunked_embs, n_components=3)
            entry["embedding"] = new_main
            entry["chunked_embeddings"] = new_chunks

        return reduced_history
