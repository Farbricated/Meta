import xml.etree.ElementTree as ET
xml = ET.parse('report.xml')
for tc in xml.findall('.//testcase'):
    failure = tc.find('failure')
    if failure is not None:
        print(f"FAILED: {tc.attrib['name']}")
        # just print first few lines of message to save terminal space
        msg = failure.attrib.get('message', '').splitlines()
        print("\n".join(msg[:5]))
        print("-" * 40)
