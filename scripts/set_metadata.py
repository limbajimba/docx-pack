#!/usr/bin/env python3
"""Set document properties on a .docx so the file does not carry a generator's fingerprints.

docx-js writes lastModifiedBy "Un-named" and an empty app.xml; python-docx writes creator "python-docx".
Word writes Application, Company, and real timestamps. This script sets them in place.

Usage:
  python3 set_metadata.py report.docx --creator "SilverTree Equity" --company "SilverTree Equity" \
      [--title "..."] [--subject "..."] [--last-modified-by "..."] [--application "Microsoft Office Word"] \
      [--created 2026-09-24T09:00:00Z] [--modified 2026-09-24T09:00:00Z] [--out other.docx]
"""
import argparse, datetime, os, re, shutil, tempfile, zipfile

CORE_NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/", "dcterms": "http://purl.org/dc/terms/",
    "dcmitype": "http://purl.org/dc/dcmitype/", "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}
APP_NS = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
VT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def set_tag(xml, tag, value, extra_attr=""):
    """Replace or insert <tag>value</tag> in a flat properties XML string."""
    if value is None:
        return xml
    pat = re.compile(rf"<{tag}(\s[^>]*)?>.*?</{tag}>|<{tag}(\s[^>]*)?/>", re.S)
    new = f"<{tag}{extra_attr}>{esc(value)}</{tag}>"
    if pat.search(xml):
        return pat.sub(new, xml, count=1)
    return re.sub(r"(</[^>]+>\s*)$", new + r"\1", xml, count=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx"); ap.add_argument("--out")
    ap.add_argument("--title"); ap.add_argument("--subject"); ap.add_argument("--creator"); ap.add_argument("--last-modified-by")
    ap.add_argument("--company"); ap.add_argument("--application", default="Microsoft Office Word"); ap.add_argument("--app-version", default="16.0000")
    ap.add_argument("--created"); ap.add_argument("--modified")
    a = ap.parse_args()
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    created, modified = a.created or now, a.modified or now
    lmb = a.last_modified_by or a.creator
    out = a.out or a.docx
    src = zipfile.ZipFile(a.docx)
    core = src.read("docProps/core.xml").decode("utf8") if "docProps/core.xml" in src.namelist() else (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties ' + " ".join(f'xmlns:{k}="{v}"' for k, v in CORE_NS.items()) + "></cp:coreProperties>")
    core = set_tag(core, "dc:title", a.title)
    core = set_tag(core, "dc:subject", a.subject)
    core = set_tag(core, "dc:creator", a.creator)
    core = set_tag(core, "cp:lastModifiedBy", lmb)
    core = set_tag(core, "cp:revision", "2" if lmb else None)
    core = set_tag(core, "dcterms:created", created, ' xsi:type="dcterms:W3CDTF"')
    core = set_tag(core, "dcterms:modified", modified, ' xsi:type="dcterms:W3CDTF"')
    app = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="{APP_NS}" xmlns:vt="{VT_NS}">'
           f"<Application>{esc(a.application)}</Application><DocSecurity>0</DocSecurity><ScaleCrop>false</ScaleCrop>"
           f"<Company>{esc(a.company or a.creator or '')}</Company><LinksUpToDate>false</LinksUpToDate><SharedDoc>false</SharedDoc>"
           f"<HyperlinksChanged>false</HyperlinksChanged><AppVersion>{esc(a.app_version)}</AppVersion></Properties>")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            if item.filename == "docProps/core.xml":
                dst.writestr(item, core)
            elif item.filename == "docProps/app.xml":
                dst.writestr(item, app)
            else:
                dst.writestr(item, src.read(item.filename))
        names = src.namelist()
        if "docProps/app.xml" not in names:
            dst.writestr("docProps/app.xml", app)
    src.close()
    shutil.move(tmp, out)
    print(f"metadata set on {out}: creator={a.creator!r} lastModifiedBy={lmb!r} company={a.company or a.creator!r} application={a.application!r}")


if __name__ == "__main__":
    main()
