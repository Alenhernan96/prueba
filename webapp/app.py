from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "🚀 ¡Funcionando correctamente en Render con Python 3.10!"

if __name__ == "__main__":
    app.run(debug=True)
