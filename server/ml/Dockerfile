FROM python:3.8-slim-buster


RUN apt-get update -y

# gcc compiler and opencv prerequisites
RUN apt-get -y install nano git build-essential libglib2.0-0 libsm6 libxext6 libxrender-dev sudo cmake ninja-build

# fixme to develop (src must be a local copy of sticky_pi_ml/src)

RUN pip install torch==1.6.0+cpu torchvision==0.7.0+cpu -f https://download.pytorch.org/whl/torch_stable.html

RUN pip install cython
RUN pip install -U 'git+https://github.com/cocodataset/cocoapi.git#subdirectory=PythonAPI'

RUN pip install -U 'git+https://github.com/facebookresearch/fvcore'

# Detectron2 - CPU copy
#RUN python -m pip install detectron2 -f https://dl.fbaipublicfiles.com/detectron2/wheels/cpu/index.html
#RUN python -m pip install detectron2 -f https://dl.fbaipublicfiles.com/detectron2/wheels/cpu/torch1.6/index.html

# Development packages
RUN git clone https://github.com/facebookresearch/detectron2 detectron2_repo
RUN pip install -e detectron2_repo

RUN python -m pip install git+https://github.com/sticky-pi/sticky-pi-api@develop#egg=sticky_pi_api&subdirectory=src
RUN git clone https://github.com/sticky-pi/sticky-pi-api && cd sticky-pi-api/src && git checkout develop && pip install -e .

COPY src /tmp/sticky_pi_ml
RUN pip uninstall sticky_pi_ml -y
RUN pip install -e /tmp/sticky_pi_ml

RUN apt-get -y install libgl1-mesa-dev libcairo-dev

# fixme... when stable:
#RUN pip install git+https://github.com/sticky-pi/sticky-pi-ml@develop#egg=sticky_pi_ml&subdirectory=src

RUN mkdir -p /opt/ml_bundle_dir/
RUN mkdir -p /opt/api_api_client/

COPY uid.py .

#CMD ["python", "uid.py", "-v"]
