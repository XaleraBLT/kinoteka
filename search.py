import datetime
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


def load_vectors(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["movies"], data["vectors"]


model = SentenceTransformer("./nomic-ai/nomic-embed-text-v2-moe", trust_remote_code=True, local_files_only=True)


def find_best_match(query: str, k: int = 10, filters: dict = None):
    movies, movie_vectors = load_vectors("./instance/films.json")

    if not movies or not movie_vectors:
        print("Ошибка: нет данных для поиска!")
        return []

    filtered_movies = []
    filtered_vectors = []

    if filters:
        for movie, vector in zip(movies, movie_vectors):
            matches_genre = not filters.get("genres") or any(
                genre in movie.get("genres", []) for genre in filters["genres"]
            )
            matches_year = not filters.get("years") or movie.get("release_date", "").split("-")[0] in map(str, filters[
                "years"])

            if matches_genre and matches_year:
                filtered_movies.append(movie)
                filtered_vectors.append(vector)
    else:
        filtered_movies, filtered_vectors = movies, movie_vectors

    if not filtered_movies:
        return []


    movie_vectors_np = np.array(filtered_vectors, dtype=np.float32)


    dimension = movie_vectors_np.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(movie_vectors_np)


    query_vector = model.encode([query]) if model else np.zeros((1, dimension), dtype=np.float32)

    query_vector_np = np.array(query_vector, dtype=np.float32)

    if query_vector_np.shape[1] != dimension:
        print(f"Ошибка: размерность запроса {query_vector_np.shape[1]} не совпадает с размерностью индекса {dimension}")
        return []


    _, indices = index.search(query_vector_np, k=min(k, len(filtered_movies)))


    best_matches = [{**filtered_movies[idx]} for idx in indices[0]]

    return best_matches


if __name__ == "__main__":
    while True:
        query = input("Описание фильма: ")
        filters = eval(input("Фильтра: "))

        k = datetime.datetime.now()
        best_movies = find_best_match(query, 10, filters)

        for i, movie in enumerate(best_movies, 1):
            print(f"{i}. {movie['title']}")
        print(datetime.datetime.now() - k)
