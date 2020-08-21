FROM heroku/miniconda:3

RUN conda install --channel alubbock --channel conda-forge graphviz pygraphviz=1.5
# NOTE: the following conda install is additional and specific to heroku docker
RUN conda install --channel conda-forge ciso8601

# Grab pip requirements.txt
ADD ./requirements.txt /tmp/requirements.txt
# Install dependencies with pip
RUN pip install --upgrade pip
RUN pip install gunicorn
RUN pip install -r /tmp/requirements.txt \
    --index-url https://pypi.org/simple \
    --extra-index-url https://test.pypi.org/simple/ \
    --default-timeout=1000
    #--no-use-pep517


# Add app code
ADD ./arya /opt/OrgMiner-Arya/arya/
ADD ./run.py /opt/OrgMiner-Arya/run.py
WORKDIR /opt/OrgMiner-Arya

#CMD gunicorn --bind 0.0.0.0:$PORT run.py
CMD gunicorn --bind 0.0.0.0:$PORT 'arya:create_app(demo=True)'
