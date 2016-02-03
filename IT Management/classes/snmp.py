from pysnmp.entity.rfc3413.oneliner import cmdgen


def get(community_string, ip, mib, request):
    cmdGen = cmdgen.CommandGenerator()
    value = ()
    oid = ()

    errorindication, errorstatus, errorindex, varbindtable = cmdGen.bulkCmd(
            cmdgen.CommunityData(community_string),
            cmdgen.UdpTransportTarget((ip, 161)),
            0,
            1,
            cmdgen.MibVariable(mib, request)
    )
    varbindtable.pop()
    if errorindication:
        print(ip + ':' + errorindication)
    if errorstatus:
        try:
            print('%s at %s' % (errorstatus.prettyPrint(), errorindex and varbindtable[int(errorindex) - 1] or '?'))
        except AttributeError:
            print('%s at %s' % (errorstatus, errorindex and varbindtable[int(errorindex) - 1] or '?'))
    else:
        for varBindTableRow in varbindtable:
            for x, y in varBindTableRow:
                oid = oid + (x.prettyPrint(),)
                value = value + (y.prettyPrint(),)
    return value, oid

