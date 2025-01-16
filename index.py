import jinja2
templdir = "/Users/newbrie/Documents/ReformUK/GitHub/ElectorWalks/templates"
workdir = "/Users/newbrie/Sites"
testdir = "/Users/newbrie/Documents/ReformUK/ElectoralRegisters/Test"
bounddir = "/Users/newbrie/Documents/ReformUK/Code/Boundaries"
#!/usr/bin/python


templateLoader = jinja2.FileSystemLoader(searchpath=templedir)
templateEnv = jinja2.Environment(loader=templateLoader)
TEMPLATE_FILE = "ElectorWalks2.html"
template = templateEnv.get_template(TEMPLATE_FILE)
outputText = template.render()  # this is where to put args to the template renderer
