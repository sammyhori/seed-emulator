from xmlrpc.client import boolean
import docker
from docker import DockerClient
from docker.models.containers  import *
import tarfile
import io, json
from os import mkdir, chdir, getcwd, path
from shutil import rmtree
import yaml
from seedemu import *

ContainerLabel: Dict[str, str] = {}
ContainerLabel['class'] = 'org.seedsecuritylabs.seedemu.meta.class'

class DockerController:
    """!
    @brief Docker controller class.

    This class represents a docker controller.
    """

    __client:DockerClient

    def __init__(self):
        """!
        @brief Docker controller construnctor
    
        """
        self.__client = docker.from_env()


    def getContainerById(self, id:str) -> Container:
        container = self.__client.containers.get(container_id=id)
        return container

    def getContainersByClassName(self, className:str) -> ContainerCollection:
        all_containers = self.__client.containers.list()
        containers = []
        classes = []
        for container in all_containers:
            if ContainerLabel['class'] in container.attrs['Config']['Labels'].keys():
                classes = json.loads(container.attrs['Config']['Labels'][ContainerLabel['class']])
                if className in classes:
                    containers.append(container)
        return containers

    # spell out whole thing when naming method.
    def executeCommandInContainer(self, container:Container, cmd, detach:bool=False, workdir:str=None) -> str:
        """!
        Args:
            cmd (str or list): Command to be executed
            detach (bool): If true, detach from the exec command.
                Default: False
            workdir (str): Path to working directory for this exec session

        Returns:
            (ExecResult): A tuple of (exit_code, output)
                exit_code: (int):
                    Exit code for the executed command or ``None`` if
                    either ``stream`` or ``socket`` is ``True``.
                output: (generator, bytes, or tuple):
                    If ``stream=True``, a generator yielding response chunks.
                    If ``socket=True``, a socket object for the connection.
                    If ``demux=True``, a tuple of two bytes: stdout and stderr.
                    A bytestring containing response data otherwise.
        """
        result = container.exec_run(cmd=cmd, detach=detach, workdir=workdir)
        
        assert result.exit_code == 0, "exit_code: "+str(result.exit_code)+"\n"+result.output.decode()

        return result.output.decode()

    def executeCommandInContainers(self, containers:ContainerCollection, cmd, detach:bool=False, workdir:str=None) -> Dict:
        assert containers != [], 'containers is empty'
        results={}
        for container in containers:
            result = container.exec_run(cmd=cmd, detach=detach, workdir=workdir)
            results[container.name]=result

        return results

    def getNetworkInfo(self, container:Container) -> dict:
        networkInfo = json.loads(self.executeCommandInContainer(container=container, cmd="ip -j addr"))
        return networkInfo

    #tarFile update needed
    def copyFileFromContainer(self, container:Container, src:str):
        bits, stat = container.get_archive(src)
        file = b"".join(bits)

        tar = tarfile.TarFile(fileobj=io.BytesIO(file))
        tar.extractall()
        
    def printFileFromContainer(self, container:Container, src:str):
        bits, stat = container.get_archive(src)
        file = b"".join(bits)

        tar = tarfile.TarFile(fileobj=io.BytesIO(file))
        for member in tar:
            print(tar.extractfile(member.name).read().decode())

    def buildImage(self, buildPath:str, tag:str):        
        self.__client.images.build(path=buildPath, tag=buildPath)
        

    def startContainer(self, name:str, image:str, networks:list, labels:dict):
        client = self.__client
        output = "output"

        if client.containers.list(all=True, filters={'name':dcInfo['container_name']}) != []:
            client.containers.list(all=True, filters={'name':dcInfo['container_name']})[0].stop()
            client.containers.prune()    

        
        container = client.containers.create(image = image, 
                            cap_add=['ALL'], 
                            sysctls={'net.ipv4.ip_forward':1, 
                                        'net.ipv4.conf.default.rp_filter':0, 
                                        'net.ipv4.conf.all.rp_filter':0},
                            privileged=True,
                            name=name, 
                            network=networks[0],
                            labels=labels)

        client.networks.get(output+"_"+networks[0]).disconnect(container)
        for network in networks:
            client.networks.get(output+"_"+network).connect(container, ipv4_address=dcInfo['networks'][network]['ipv4_address'])
        
        container.start()


