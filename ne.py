# NewExe (NE) Segment Manipulation Tool
# (C) 2023 Serhii Liubshin
# License - simply give credit where due
# I don't think this would see much use nowadays
# Might be useful for software archeologists though :D
#
# Driver resources problem solved
# In drivers they are put between unmovable undiscardable segments
# So we need to keep them that way

import struct
import sys

print ('NE (NewExe) segment manipulation tool')
print ('(C) 2023 Serhii Liubshin')

if len(sys.argv) < 2:
  print('Usage: python',sys.argv[0],'<input> [output] [segment] [pages]')
  print("[segment]: segment to modify, first is 1, by it's number in segment table")
  print('[pages]: pages (bytes*pagesize, usually 16) to add to segment')
  exit()

ine = open(sys.argv[1],'rb')

header = ine.read(2)
if (header!=b'MZ'):
  print("Invalid MZ signature!")
  exit()     

ine.seek(60)
neoffset = struct.unpack('<I',ine.read(4))[0]
ine.seek(neoffset)

header = ine.read(2)
if (header!=b'NE'):
  print("Invalid NE signature!")
  exit()

header = struct.unpack('<BBHHIBBBBHHIIHHHHHHHHIHHHBBHHHBB',ine.read(62))

segcount = header[13]
ashift = header[23]
segtable = header[16]
restable = header[17]
rescount = header[24]

print('segcount: ',segcount,'align shift: ',ashift)
print('segtable: ',segtable,'restable: ',restable)
if (rescount==0):
  print("Resource count undefined")

segarr = []
segdata = []

segs = 0

for i in range(segcount):
  ine.seek(segtable+neoffset+i*8)
  segt = struct.unpack('<HHHH',ine.read(8))
  #Segment number, segment info: 
  segt = (i,) + segt
  ine.seek(int(segt[1]<<ashift))
  #Read segment data
  segdata.append(bytearray(ine.read(int(segt[2]))))
  #Add extra segment data 
  so=int(segt[1]<<ashift)+int(segt[2])
  ine.seek(so)
  dc = struct.unpack('<H',ine.read(2))[0]
  segt = segt + (dc,)
  for j in range(dc):
    #We don't exactly care for contents
    segt = segt + struct.unpack('<Q',ine.read(8))
  segarr.append(segt)

  nextpos = int(segarr[i][1]<<ashift)+int(segarr[i][2])+2+int(segarr[i][5])*8

  if not (int((nextpos>>ashift)<<ashift) == int(nextpos)):
    nextpos = ((nextpos>>ashift)+1)<<ashift

  print('segment:', int(segarr[i][0]+1),'offset:',hex(segarr[i][1]<<ashift),'size:',hex(segarr[i][2]),'relocs:',segarr[i][5])
  #,'next ppos:',hex(nextpos))
  segs = segs + int(segarr[i][2]) + 2 + int(segarr[i][5])*8
print(segs,'bytes total')

resarr = []
resdata = []
resseg = []

ine.seek(restable+neoffset)
rshift = struct.unpack('<H',ine.read(2))[0]

#resstart = 65536

rcount = 0
rsize = 0

#func to sort segments by file offset
def offset(val):
  return val[1] 

segarr.sort(key=offset)

def res_segment(ro):
  segnum=0
  #print(hex(ro))
  for i in range(segcount):
    if (ro > int(segarr[i][1]<<ashift)):
      #print(hex(ro),(hex(int(segarr[i][1]<<ashift))),segarr[i][0])
      segnum = segarr[i][0]
  return segnum

print("Resources:")
while True:
#2Do - named resources
  #If resource type 0 - terminate
  rest = struct.unpack('<H',ine.read(2))
  if (rest[0] == 0):
    break
  if (rest[0] and 0x8000):
    restype = "Int"
  else:
    restype = "String"
    print("Named resources unsupported right now.")
    exit()
  #Count of this resource + reserved
  resn = struct.unpack('<HI',ine.read(6))
  print("type",hex(rest[0]),resn[0],"items")
  restup = ()
  for i in range(resn[0]):
    #Offset, length, flag, id, reserved
    restemp = struct.unpack('<HHHHI',ine.read(12))
    tpos = ine.tell()
    #Get segment this resource if located after
    resseg.append(res_segment(int(restemp[0]<<rshift)))
    #print(resseg[-1]+1)
    #Read resource
    ine.seek(int(restemp[0]<<rshift))
    resdata.append(bytearray(ine.read(int(restemp[1]<<rshift))))
    rcount = rcount + 1
    rsize = rsize + int(restemp[1]<<rshift)
    ine.seek(tpos)
    #Length is stated in bytes in docs. I believe that's wrong and length is in pages
    #print(hex(restemp[0]<<rshift),hex(restemp[1]<<rshift))
    #if (restemp[0]<resstart):
    #  resstart = restemp[0]
    restup = restup + restemp
  rest = rest + resn + restup
  #Rest: Type DW, Count DW, Reserved DD, Offset DW, Length DW, Flag DW, ID DW, Reserved DD

  resarr.append(rest)

print("Loaded",rcount,"resources,",rsize,"bytes")

#Now, let's get our buffers


#We'll use this blocks:
#Begin - from file start to first physical segment
#Array of segments
#Trail - resources

#Sort segments by file offset
segarr.sort(key=offset)
segstart = int(segarr[0][1]<<ashift)

#for i in range(segcount):
#  print(segarr[i][0],segarr[i][1])
        
#print(hex(segstart))

ine.seek(0)
startblock = bytearray(ine.read(segstart))

#Well, we got what we need
ine.close();

if len(sys.argv)<3:
  exit()

incseg = -1
if len(sys.argv)>3:
  incseg = int(sys.argv[3]) - 1

incpage = 1
if len(sys.argv)>4:
  incpage = int(sys.argv[4])

if not (ashift == rshift):
  print("Page size differs for segment and resources")

print("Reworking segments...")

#Increase requested segment
if (incseg > -1):
  segarr.sort()
  for i in range(segcount):
    if (segarr[i][0] == incseg):
      seglist = list(segarr[i])
      #Disk size
      seglist[2] = seglist[2] + (incpage<<ashift)
      #Alloc size
      seglist[4] = seglist[4] + (incpage<<ashift)
      segarr[i] = tuple(seglist)
  segarr.sort(key=offset)

for i in range(segcount-1):

  #Fixme: use rshift if resources are present after segment
  #Now i just hope rshift = ashift
  nextoff = int(segarr[i][1]<<ashift)+int(segarr[i][2])+2+int(segarr[i][5])*8

  #We need to understand size of resources located inbetween segments or drivers won't work
  for j in range(rcount):
    if (resseg[j] == segarr[i][0]):
      nextoff = nextoff + len(resdata[j])

  #Quick fixup 
  #+2?
  nextoff = int(nextoff>>ashift)+1

  #print(nextoff)

  seglist = list(segarr[i+1])

  #print(segarr[i][0],seglist[1]-int(nextoff),"pages diff so far")
  seglist[1] = int(nextoff)

  segarr[i+1] = tuple(seglist)

segarr.sort()

#Calculate resource offset for each segment
segresoffset = []
for i in range(segcount):
  resoff = int(segarr[i][1]<<ashift)+int(segarr[i][2])+2+int(segarr[i][5])*8
  resoff = int(resoff>>rshift)+1
  segresoffset.append(resoff)

print("Creating",sys.argv[2],"...")
one = open(sys.argv[2],'wb')

one.write(startblock)
for i in range(segcount):
  #Write segment table record
  one.seek(segtable+neoffset+i*8)
  one.write(struct.pack('<HHHH',segarr[i][1],segarr[i][2],segarr[i][3],segarr[i][4]))
  #Write segment
  one.seek(int(segarr[i][1]<<ashift))
  one.write(segdata[i])
  #Seek to end of phys size
  one.seek(int(segarr[i][1]<<ashift) + int(segarr[i][2]))  
  #Write relocs
  one.write(struct.pack('<H',segarr[i][5]))
  for j in range(segarr[i][5]):
    one.write(struct.pack('Q',segarr[i][6+j]))


print("Writing resources...")

rc = 0
#First is shift
one.seek(restable+neoffset)
one.write(struct.pack('<H',rshift))
for i in range(len(resarr)):
  #Type, count, reserved
  one.write(struct.pack('<HHI',resarr[i][0],resarr[i][1],resarr[i][2]))
  reslist = list(resarr[i])
  #Offset, Length, ...
  for j in range(int(reslist[1])):
    r_seg = resseg[rc]
    reslist[j*5+3] = segresoffset[r_seg]
    r_len = reslist[j*5+4]
    pushpos = one.tell()
    one.seek(int(segresoffset[r_seg]<<rshift))
    one.write(resdata[rc])
    rc = rc + 1
    segresoffset[r_seg] = segresoffset[r_seg] + r_len
    one.seek(pushpos)
    one.write(struct.pack('<HHHHI',reslist[j*5+3],reslist[j*5+4],reslist[j*5+5],reslist[j*5+6],reslist[j*5+7]))

'''
one.seek(0,2)
#Write resources
#Position to the end alighned with resource shift
one.seek(((one.tell()>>rshift)+1)<<rshift)
resoffset = one.tell()
croffset = resoffset
#Rest: Type DW, Count DW, Reserved DD, Table: Offset DW, Length DW, Flag DW, ID DW, Reserved DD
#Create new resource table with new offsets
one.seek(restable+neoffset)
one.write(struct.pack('<H',rshift))
for i in range(len(resarr)):
  one.write(struct.pack('<HHI',resarr[i][0],resarr[i][1],resarr[i][2]))
  reslist = list(resarr[i])
  #print(reslist)
  for j in range(int(reslist[1])):
    reslist[j*5+3] = int(croffset>>rshift)
    croffset = croffset + int(reslist[j*5+4]<<rshift)
    one.write(struct.pack('<HHHHI',reslist[j*5+3],reslist[j*5+4],reslist[j*5+5],reslist[j*5+6],reslist[j*5+7]))
#  resarr[i] = tuple(reslist)
one.seek(resoffset)
for i in range(len(resdata)):
  one.write(resdata[i])
'''

one.close
print("Done.")