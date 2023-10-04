# Docker Deployment Methods

## Docker Standalone

This method assumes you have Docker installed and running on your server.

1. Ensure you are in the root directory of the project.
2. Pull the Docker image

    ```{prompt} bash
    docker pull gcr.io/censys-io/censys-cloud-connector:latest
    ```

    ````{admonition} Note
    :class: censys
    If your environment does not allow you to pull the Docker image, you can
    build it from the Dockerfile using the following command. You can then
    push the image to a Docker registry.

    ```{prompt} bash
    docker build -t gcr.io/censys-io/censys-cloud-connector:latest .
    ```
    ````

3. Run the Docker container

The following command will run the Docker container.
The container also requires the `providers.yml` file. The `-v` flag will
mount the `providers.yml` file as a volume. If your `providers.yml` references
additional secret files, you can mount it as a volume as well. The `-d` flag
is used to run the container in the background. We also include the `--rm`
flag to ensure the container is removed after it has finished.

- Run the Docker container (Once)

    ```{prompt} bash
    docker run -d --rm \
        --env-file .env \
        -v $(pwd)/providers.yml:/app/providers.yml \
        -v $(pwd)/secrets:/app/secrets \
        gcr.io/censys-io/censys-cloud-connector:latest
    ```

- Run the Docker container (Scheduled)

    ```{prompt} bash
    docker run -d --rm \
        --env-file .env \
        -v $(pwd)/providers.yml:/app/providers.yml \
        -v $(pwd)/secrets:/app/secrets \
        gcr.io/censys-io/censys-cloud-connector:latest \
        /app/.venv/bin/censys-cc scan --daemon 4
    ```

    ```{admonition} Note
    :class: censys
    The {doc}`--daemon <cli>` flag will run the connector in the background.
    The number specifies the number of hours between each scan.
    ```

- Run the Docker container (Without secrets mounted)

    ```{prompt} bash
    docker run -d --rm \
        --env-file .env \
        -v $(pwd)/providers.yml:/app/providers.yml \
        gcr.io/censys-io/censys-cloud-connector:latest
    ```

## Docker Compose

This method assumes you have Docker and Docker Compose installed and running on
your server.

1. Run the Docker Compose file

    ```{prompt} bash
    docker-compose up -d
    ```

2. (Optional) Run your connector on a scheduled interval

    Uncomment the line `# command: scan --daemon 4` in `docker-compose.yml`.

    ```{admonition} Note
    :class: censys
    Learn more about the available options for the {doc}`scan <cli>` command.
    ```
