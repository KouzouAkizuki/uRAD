# uRAD

Partiendo de la instalacion de Raspbian - RPI4 - Bookworm - python 3.11.2

Importante activar el SPI de la raspberry pi

## Pip for external enviroments

```shell
sudo nano /etc/pip.conf
```

Añadir la siguiente linea al bash

```shell
break-system-packages = true
```

## Pyqtgraph

```shell
sudo pip install pyqtgraph
sudo apt install -y libatlas-base-dev
```

## Scipy

```shell
sudo apt-get install python3-scipy
```

## Repositorio

```shell
git clone https://github.com/KouzouAkizuki/uRAD.git
```