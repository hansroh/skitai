# Patch for using with Vue.js namespace and v-on shortcut
# 2017. 2.17 by Hans Roh

from chameleon import tokenize, parser
import re

a = tokenize.collector.add

# change only this line, just add @ for v-on shortcut
a ("NameStrt", "[A-Za-z_:@]|[^\\x00-\\x7F]")

# these're just consequece for recompiling tokenize.re_xml_spe
a ("Name", "(?:%(NameStrt)s)(?:%(NameChar)s)*")
a("ElemTagCE",
  "(%(Name)s)(?:(%(S)s)(%(Name)s)(((?:%(S)s)?=(?:%(S)s)?)"
  "(?:%(AttValSE)s|%(Simple)s)|(?!(?:%(S)s)?=)))*(?:%(S)s)?(/?>)?")
a("MarkupSPE",
  "<(?:!(?:%(DeclCE)s)?|"
  "\\?(?:%(PI_CE)s)?|/(?:%(EndTagCE)s)?|(?:%(ElemTagCE)s)?)")
a("XML_SPE", "%(TextSE)s|%(MarkupSPE)s")

tokenize.re_xml_spe = re.compile(tokenize.collector.res['XML_SPE'])

# for ignoring namespace exception
def unpack_attributes(attributes, namespace, default):
    namespaced = parser.OrderedDict()

    for index, attribute in enumerate(attributes):
        name = attribute['name']
        value = attribute['value']
        if ':' in name:
            prefix = name.split(':')[0]
            name = name[len(prefix) + 1:]
            try:
                ns = namespace[prefix]
            except KeyError:
                ns = default
                # disabling exception
                #raise KeyError(
                #    "Undefined namespace prefix: %s." % prefix)
        else:
            ns = default
        namespaced[ns, name] = value

    return namespaced
    
parser.unpack_attributes  = unpack_attributes


