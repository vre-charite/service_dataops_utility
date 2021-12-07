# DataOps Utility Service

This service contains dataops that should not have access to greenroom. It's built using the FastAPI python framework.

## Installation

### Install requirements

`pip install -r requirements.txt`

Run the service with uvicorn
`python app.py`

### Docker

*docker-compose*

`docker-compose build`
`docker-compose up`

*Plain old docker*

`docker build . -t service_data_ops`
`docker run service_data_ops`






