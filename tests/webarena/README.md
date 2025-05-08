
## Python env setup
1. download this repo
```bash
cd $WORKDIR
git clone https://github.com/minmin-intel/BrowserGym.git
```

2. create conda env
```bash
conda create -n browser-gym-env python=3.10
```

3. install browser-gym and other packages
```bash
cd BrowserGym
make install
pip install openai
```

## WebArena env setup
1. clone the setup repo
```bash
cd $WORKDIR
git clone https://github.com/minmin-intel/webarena-setup.git
git checkout test-webarena
```

2. Follow the instructions on this [README](https://github.com/minmin-intel/webarena-setup/blob/main/webarena/README.md)
```bash
# download the shopping-admin docker image
cd $WORKDIR
mkdir webarena_docker_images
cd webarena_docker_images
wget http://metis.lti.cs.cmu.edu/webarena-images/shopping_admin_final_0719.tar
```
Note: we will only test the shopping-admin tasks, so only need to download `shopping_admin_final_0719.tar`, no need to download other docker image tars or the map related files.

Then follow the instructions to run 01 to 06 bash scripts.

## Run demo agent test
```bash
cd $WORKDIR/BrowserGym/demo_agent
bash test_demo_agent.sh
```
