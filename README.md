# StockBot

# Introduction
A Discord bot to display stock information

# Dev
## Development Environment Stack
- [Docker](https://docs.docker.com/)
  * Containerizes `MySQL` and the bot's run environment
- [Docker Compose](https://docs.docker.com/compose/)
  * Orchestrates `Docker` containers
- [PyInvoke](http://www.pyinvoke.org/)
  * Runs pre-set task commands in one line using `tasks.py`
- [Pipenv](https://github.com/pypa/pipenv)
  * Uses `Pipfile` and `Pipefile.lock` to manage dependencies
  
## Requirements
* `Python 3.9.x`
* Pipenv - `pip install pipenv`  
* PyInvoke - `pip install invoke`  
* Docker & Docker Compose - https://docs.docker.com/get-docker/

## Getting Started on Developing
Before doing anything :  
  * ***Make sure you are in the root directory of this project***
  * Create a `.env` file in the root directory
  * In `.env`, put your tokens in
    ```
    TOKEN=bot-token-here
    RAPID-API-KEY=rapid-api-key-here
    DATABASE_URL=mysql+pymysql://root:root@mysql/stockbot?charset=utf8mb4
    ```  

Step-by-step :
1. `invoke build`
    * Builds the Docker containers needed to run this project
2. `invoke dev`
    * Runs the containers and prompt you when they are done
3. `invoke runbot`
    * Runs the bot
    
## Altering Dependencies
Currently, the project is using `Pipenv` to manage dependencies.
However, the container for the worker is using `requirements.txt`.

Step-by-step :
1. `Pipenv [install|uninstall|upgrade] package`
    * This will update your own dependencies
2. `invoke requirements`
    * Converts `Pipenv` dependencies into `requirements.txt`
