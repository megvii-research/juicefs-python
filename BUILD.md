## Build libjfs.so

### Install go

```shell
sudo add-apt-repository ppa:longsleep/golang-backports
sudo apt update
sudo apt install golang-go
```

### Download JuiceFS Source Code

```shell
git clone https://github.com/juicedata/juicefs.git
```

Better to checkout to the last release version.

### Install Dependencies

```shell
go mod download
```

### Build

```shell
cd sdk/java/libjfs
make libjfs.so
```

