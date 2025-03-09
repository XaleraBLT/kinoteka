import json
import random
import pandas as pd
import sqlite3
from search import find_best_match

def get_recommendation(user_id, top_n=20):
    conn = sqlite3.connect("./instance/site.db")

    query_ratings = "SELECT user_id, film_title, rating FROM rating WHERE user_id = ?"
    history = "SELECT user_id, film_title FROM viewing_history WHERE user_id = ?"

    ratings_df = pd.read_sql(query_ratings, conn, params=(user_id,))
    history_df = pd.read_sql(history, conn, params=(user_id,))

    conn.close()

    with open("./instance/films.json", "r", encoding="utf-8") as f:
        films_data = json.load(f)

    movies_df = pd.DataFrame(films_data["movies"])

    search_history = set(history_df["film_title"].tolist())
    rated_movies = set(ratings_df[ratings_df["rating"] >= 7]["film_title"].tolist())

    history_recs = []
    if search_history:
        for searched_title in search_history:
            searched_movie = movies_df[movies_df["title"] == searched_title]
            if not searched_movie.empty:
                searched_movie = searched_movie.iloc[0]
                description = searched_movie["description_mini"]
                filters = {"genre": searched_movie["genres"], "year": searched_movie["release_date"][:4]}
                results = find_best_match(description, round(top_n), filters)
                if results:
                    history_recs += results[1:]

    rate_recs = []
    if rated_movies:
        for rated_title in rated_movies:
            rated_movie = movies_df[movies_df["original_title"] == rated_title]
            if not rated_movie.empty:
                rated_movie = rated_movie.iloc[0]
                description = rated_movie["description_mini"]
                filters = {"genre": rated_movie["genres"], "year": rated_movie["release_date"][:4]}
                results = find_best_match(description, round(top_n), filters)
                if results:
                    rate_recs += results[1:]

    recommended_movies = []
    if history_recs:
        recommended_movies += random.sample(history_recs, round(0.25 * top_n))
    if rate_recs:
        recommended_movies += random.sample(rate_recs, round(0.75 * top_n))

    if recommended_movies:
        random.shuffle(recommended_movies)

    films = {film["title"]: film for film in recommended_movies}

    return films
