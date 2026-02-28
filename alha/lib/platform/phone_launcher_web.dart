/// Web implementation — opens the tel: URI via a synthetic anchor click.
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

void launchPhoneCall(String phone) {
  html.AnchorElement(href: 'tel:$phone')..click();
}
