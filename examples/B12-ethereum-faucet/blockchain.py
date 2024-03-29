#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import sys
from eth_account import Account


emu = Makers.makeEmulatorBaseWith10StubASAndHosts(1)

# Create the Ethereum layer
# saveState=True: will set the blockchain folder using `volumes`, 
# so the blockchain data will be preserved when containers are deleted.
eth = EthereumService(saveState = True, override=True)

# Create a POA Blockchain layer, which is a sub-layer of Ethereum layer
# Need to specify chainName and consensus when create Blockchain layer.
blockchain1 = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)

# Create blockchain1 nodes (POA Etheruem) (nodes in this layer are virtual)
e1 = blockchain1.createNode("poa-eth1").enableGethHttp()
e2 = blockchain1.createNode("poa-eth2").enableGethHttp()
e3 = blockchain1.createNode("poa-eth3").enableGethHttp()
e4 = blockchain1.createNode("poa-eth4").enableGethHttp()
e5 = blockchain1.createNode("poa-eth5").enableGethHttp()
e6 = blockchain1.createNode("poa-eth6").enableGethHttp()
e7 = blockchain1.createNode("poa-eth7").enableGethHttp()
e8 = blockchain1.createNode("poa-eth8").enableGethHttp()

# Set bootnodes on e1 and e5. The other nodes can use these bootnodes to find peers.
# Start mining on e1,e2, e5, and e6
# To start mine(seal) in POA consensus, the account should be unlocked first. 
e1.setBootNode(True).unlockAccounts().startMiner()
e2.unlockAccounts().startMiner()
e5.setBootNode(True).unlockAccounts().startMiner()
e6.unlockAccounts().startMiner()

# Customizing the display names (for visualization purpose)
emu.getVirtualNode('poa-eth1').setDisplayName('Ethereum-POA-1')
emu.getVirtualNode('poa-eth2').setDisplayName('Ethereum-POA-2')
emu.getVirtualNode('poa-eth3').setDisplayName('Ethereum-POA-3').addPortForwarding(8545, 8540)
emu.getVirtualNode('poa-eth4').setDisplayName('Ethereum-POA-4')
emu.getVirtualNode('poa-eth5').setDisplayName('Ethereum-POA-5')
emu.getVirtualNode('poa-eth6').setDisplayName('Ethereum-POA-6')
emu.getVirtualNode('poa-eth7').setDisplayName('Ethereum-POA-7')
emu.getVirtualNode('poa-eth8').setDisplayName('Ethereum-POA-8')

# Binding virtual nodes to physical nodes
emu.addBinding(Binding('poa-eth1', filter = Filter(asn = 150, nodeName='host_0')))
emu.addBinding(Binding('poa-eth2', filter = Filter(asn = 151, nodeName='host_0')))
emu.addBinding(Binding('poa-eth3', filter = Filter(asn = 152, nodeName='host_0')))
emu.addBinding(Binding('poa-eth4', filter = Filter(asn = 153, nodeName='host_0')))
emu.addBinding(Binding('poa-eth5', filter = Filter(asn = 160, nodeName='host_0')))
emu.addBinding(Binding('poa-eth6', filter = Filter(asn = 161, nodeName='host_0')))
emu.addBinding(Binding('poa-eth7', filter = Filter(asn = 162, nodeName='host_0')))
emu.addBinding(Binding('poa-eth8', filter = Filter(asn = 163, nodeName='host_0')))

# Faucet Service



# Generate a new Ethereum account for the Owner of faucet account
faucet_owner_account = Account.create()

# Add the ethereum using the EthereumService
blockchain1.addLocalAccount(address=faucet_owner_account.address, balance=1000, unit=EthUnit.ETHER)

faucetService = FaucetService()
faucet:FaucetServer = faucetService.install('faucet')
faucet.setOwnerPrivateKey(keyString=faucet_owner_account.privateKey.hex(), isEncrypted=False)
faucet.setPort(80)
faucet.setChainId(blockchain1.getChainId())
faucet.setConsensusMechanism(ConsensusMechanism.POA)

# if user know the url of the eth node,
# user can use faucet::setRpcUrl method instead.
# But in this scenario, we have no information of the ip address of eth5 node.
# So, we are using FaucetService::setRpcUrlByVirtualNodeName method to link the faucet service to the ethnode specified.
# Make sure that eth5 node has enabled geth.

faucet.setRpcUrlByVirtualNodeName('poa-eth5')
# Enable http connection on e5 geth
e5.enableGethHttp()

faucet.fund('0x72943017a1fa5f255fc0f06625aec22319fcd5b3', 2)
faucet.fund('0x5449ba5c5f185e9694146d60cfe72681e2158499', 5)

emu.addBinding(Binding('faucet', filter=Filter(asn=154, nodeName='host_0')))

###############################################################
# Faucet User Server Example => chainlink
faucetUser = FaucetUserService()
faucetUser.setFaucetServerInfo(vnode = 'faucet', port=80)
faucetUser.install('faucet_user')

emu.addBinding(Binding('faucet_user', filter=Filter(asn=164, nodeName='host_0')))

# Add the layer and save the component to a file
emu.addLayer(eth)
emu.addLayer(faucetService)
emu.addLayer(faucetUser)
emu.dump('component-blockchain.bin')

emu.render()

if len(sys.argv) == 1:
    platform = "amd"
else:
    platform = sys.argv[1]

platform_mapping = {
    "amd": Platform.AMD64,
    "arm": Platform.ARM64
}
docker = Docker(etherViewEnabled=True, platform=platform_mapping[platform])

# If output directory exists and override is set to false, we call exit(1)
# updateOutputdirectory will not be called
emu.compile(docker, './output', override=True)
