import invoke

@invoke.task(help={"arg": "(Takes docker-compose arguments. Use quotes for multiple arguments.)"})
def compose(c, arg):
    """
    Acts as docker-compose
    """
    c.run(f"docker-compose -f docker/docker-compose.yml {arg}", pty=False)


@invoke.task
def exec(c):
    """
    Gets you into the docker container shell
    """
    compose(c, "exec stockbot /bin/bash")


@invoke.task
def build(c):
    """
    Builds the containers
    """
    compose(c, "build")


@invoke.task(help={"verbose": "(Prints docker-compose log in real time)"})
def dev(c, verbose=True):
    """
    One-button solution for getting the containers up and run the bot
    """
    if verbose:
        compose(c, "up")
    else:
        compose(c, "up -d")
    print("Containers are now up.")
    print("Running bot ...")
    runbot(c)


@invoke.task
def requirements(c):
    """
    Exports your pipenv environment to requirements.txt
    """
    c.run("pipenv run pip freeze > requirements.txt")


@invoke.task
def runbot(c):
    """
    Runs the bot
    """
    compose(c, "exec stockbot python /apps/stockbot/stockbot.py")
