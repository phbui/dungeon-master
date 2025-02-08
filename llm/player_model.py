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
        reduced_history = copy.deepcopy(self.history)
        
        def reduce_embeddings(embeddings, n_components=3):
            total_var = np.sum(np.var(embeddings, axis=0))
            if total_var < 1e-8:
                result = embeddings[:, :n_components]
            else:
                pca = PCA(n_components=n_components)
                result = pca.fit_transform(embeddings)
            if result.shape[1] < n_components:
                pad_width = n_components - result.shape[1]
                result = np.hstack([result, np.zeros((result.shape[0], pad_width))])
            return result

        # Process main embeddings for all history entries.
        main_embeddings = np.array([entry["embedding"] for entry in reduced_history])
        if len(main_embeddings) == 1:
            reduced_main_embeddings = main_embeddings[:, :3]
        else:
            reduced_main_embeddings = reduce_embeddings(main_embeddings, n_components=3)
        
        for i, entry in enumerate(reduced_history):
            entry["embedding"] = reduced_main_embeddings[i]
            # Now reduce the dimensionality of chunked embeddings if present.
            if "chunked_embeddings" in entry and entry["chunked_embeddings"]:
                chunk_embs = np.array(entry["chunked_embeddings"])
                if chunk_embs.shape[0] == 1:
                    reduced_chunk_embs = chunk_embs[:, :3]
                else:
                    reduced_chunk_embs = reduce_embeddings(chunk_embs, n_components=3)
                entry["chunked_embeddings"] = reduced_chunk_embs

        return reduced_history
