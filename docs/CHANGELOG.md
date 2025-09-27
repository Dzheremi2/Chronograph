## 4.2.2

<p>Hotfix</p>
<ul>
  <li>Previously, LRClib publisher always ends with an error cause of programmatical error</li>
  <li>FLAC files without album cover now correctly display cover placeholder</li>
</ul>

## 4.2.1

<p>New features</p>
<ul>
  <li>"Delete Lyrics" button added to Metadata Editor dialog</li>
</ul>
<p>Bug fixes</p>
<ul>
  <li>"Embed lyrics default format" toggle labels not ellipsizing anymore</li>
  <li>Empty lyric files are now removing automatically</li>
</ul>

## 4.2

<p>New features</p>
<ul>
  <li>Migrate to GNOME Platform 49 </li>
  <li>New shortcuts dialog from LibAdwaita 1.8</li>
</ul>
<p>Bug fixes</p>
<ul>
  <li>If you have files opened independently (not a directory) and Open/Drag-n-Drop new ones, the previous won't be removed</li>
  <li>"Add to Saves" button now won't be visible if app startup with saved session</li>
  <li>Saved Location now properly selecting on app startup with saved session</li>
</ul>

## 4.1

<p>New features</p>
<ul>
  <li>Added ability to embed lyrics to the audio file. It works automatically and manually (from the Sync Page)</li>
  <li>Added "Show" button to the "Path" row in About File dialog</li>
  <li>Preferences are now have searching ability</li>
</ul>
<p>Bug fixes</p>
<ul>
    <li>eLRC prefixed files now won't create if "Save LRC along eLRC" preference is disabled. Instead, eLRC lyrics will be written to just .lrc file</li>
</ul>
<p>Miscellaneous</p>
<ul>
    <li>Line in lyrics editor on Word-by-Word sync page are now not wrapping for better distinguish of line borders</li>
    <li>The app preferences storing method changed... again. So your preferences will reset after the update. Please, consider to reconfigure the app preferences after the update. Sorry for that. Hope preferences schema won't change ever again :(</li>
</ul>
<p>Translation</p>
<ul>
    <li>Translations update</li>
</ul>

## 4.0

<p>A new eLRC format support!</p>
<p>Added support for advanced syncing Word-by-Word (WBW).</p>
<p>WBW syncing has 2 steps: Edit the lyrics you gonna sync and... sync them. Editing lyrics while syncing is not possible in WBW mode.</p>
<p>Unfortunately, LRClib does not have support for eLRC lyrics, so WBW lyrics aren't possible to upload to LRClib :(</p>
<p>Navigation in WBW syncing mode happens by using Alt+{arrow_keys}, so using WBW on mobile will be too overwhelming, so it's not recommended.</p>
<p>If the lyrics you've provided are partially synced then the app will start the synchronization from the first unsynced word.</p>
<p>Now there will be two types of files: eLRCs with eLRC prefix set up and plain .lrc</p>
<p>Don't forget to check Preferences after the update :)</p>

## 3.0.1

<p>Apologies for all Ukrainian app users. Previously, Ukrainian language was not available cause of misspelled langcode (UA instead of UK)</p>
<p>Translations</p>
<ul>
  <li>Fixed Ukrainian translation</li>
  <li>Translations update</li>
</ul>

## 3.0

<p>The App was rewritten for better performance and easier features implementation</p>
<p>New features</p>
<ul>
  <li>Added logging and debugging imformation to the About dialog</li>
</ul>
<p>Bug fixes</p>
<ul>
  <li>Precise milliseconds are now disabled by default</li>
</ul>
<p>Translations</p>
<ul>
  <li>Added Hungarian translation</li>
  <li>Translations update</li>
</ul>

## 2.5.2

<p>Bug fixes</p>
<ul>
  <li>Now if .lrc file has metatags inside of it, they wouldn't be parsed and used in the viewer, but will still present in the file and wouldn't be erased on lyrics change</li>
  <li>Scroll position of the lyrics editor now not resetting when using Enter-press line appending</li>
</ul>

## 2.5.1

<p>New features</p>
<ul>
  <li>Added preference for enabling cover images compression. Using scale from 1 to 95 where lower value means lower cover quality. May also slightly reduce memory consumption</li>
</ul>
<p>Bug fixes</p>
<ul>
  <li>Highly reduced the memory consumption by decreasing the size of the tracks covers</li>
  <li>Fixed publishing plain lyrics to LRClib</li>
</ul>

## 2.5

<p>New features</p>
<ul>
  <li>Added .opus file format support</li>
  <li>Added support for subdirectories</li>
</ul>

## 2.4.5

<p>Renaming the Saved Location now performs using dialogs instead of popovers</p>

## 2.4.4

<p>Actions with saved locations now performing using RMB click or long press</p>

## 2.4.3

<p>Bug fixes</p>
<ul>
  <li>Window control buttons on syncing page now depends on system settings</li>
  <li>LRClib Publish result toasts now shows correctly</li>
  <li>Primary app menu now opens on F10 press</li>
</ul>

## 2.4.2

<p>Bug fixes &amp; Common text editor like behavior</p>
<ul>
  <li>Rows in List View mode now all have the same size, and all images now have rounded corners</li>
  <li>Now sync lines have behavior like common text editor. When pressing Backspace on an empty line, it deletes. When pressing Enter while in line, the new line added below and focused</li>
</ul>

## 2.4.1

<p>Bug fixes</p>
<ul>
  <li>Metadata editor buttons now doesn't show if user syncing an untaggable file</li>
</ul>

## 2.4

<p>GNOME Platform 48 &amp; New features</p>
<ul>
  <li>Now you can add separate file to the library by opening them or by Drag-N-Dropping them into the window</li>
  <li>App now using GNOME Platform 48 meaning now it's using Adwaita 1.7</li>
  <li>New beautiful Adwaita 1.7 switcher in LRClib import dialog</li>
  <li>Added Dutch translation</li>
  <li>Added Estonian translation</li>
</ul>

## 2.3

<p>New features</p>
<ul>
  <li>New file formats: m4a and aac (reduced functionality)</li>
  <li>Manual LRClib publishing dialog for tracks in untaggable formats (like aac)</li>
  <li>Added Chinese (Simplified Han script) translation</li>
</ul>

## 2.2

<p>New features and bug fixes</p>
<ul>
  <li>New List View mode. Option preferred on smaller displays</li>
  <li>Option to automatically toggle List View on display resize for better experience</li>
  <li>Now, if empty directory was parsed, the specific status page will inform user about that</li>
  <li>Fixes for precise milliseconds from previous release</li>
  <li>Pin button now wouldn't appear if opened directory is already in saves</li>
  <li>Translators for your language are now mentioned in the "About App"</li>
</ul>

## 2.1

<p>New features and bug fixes</p>
<ul>
  <li>Added setting for precise milliseconds (3-digit), enabled by default</li>
  <li>Added reparse button for reparsing current directory</li>
  <li>Sorting moved to the main app menu</li>
  <li>Fixed incorrect LRClib import dialog collapsed navigation page behavior</li>
  <li>Fixed inconsistent behavior of the label of the quick edit dialog</li>
  <li>Added Portuguese (Brazil) translation</li>
  <li>Added Finnish translation</li>
</ul>

## 2.0

<p>Full app rewrite for better performance and flexibility</p>
<ul>
  <li>App has been renamed to Chronograph</li>
  <li>New icon</li>
  <li>App is now adaptive for different display sizes</li>
  <li>Added session saving</li>
  <li>Added ability to pin current directory</li>
</ul>

## 1.2.1

<p>Important hotfix of publishing functionality</p>

## 1.2

<p>LRClib import now available</p>
<ul>
  <li>Added LRClib to import from menu</li>
  <li>Search synced/plain lyrics by title and artist and import it to editor for resyncing/syncing respectively</li>
</ul>

## 1.1.1

<p>Important bug fixes</p>
<ul>
  <li>fix: fixed various bugs caused by absence of needed flatpak sanbox permissions</li>
  <li>fix: blocked ability to publish lyrics if any field is "Unknown"</li>
  <li>fix: fixed note icon on song cards if there is no cover in metainfo of file</li>
</ul>

## 1.1.0

<p>Features and bug fixes</p>
<ul>
  <li>Added ability to replay selected line</li>
  <li>Added line actions button to avoid using only hotkeys</li>
  <li>Added ability to select file format for auto manipulation</li>
  <li>fix: Added tooltips for all buttons</li>
  <li>fix: App is now not freezing while parsing large directories</li>
</ul>

## 1.0.1

<p>Features and updated icon</p>
<ul>
  <li>Added search in title and artist fields of songs</li>
  <li>Updated app icon and brand colors</li>
</ul>

## 1.0

<p>First full release</p>
<ul>
  <li>Added sorting by title from "A-Z" or from "Z-A"</li>
  <li>Added abylity for exporting lyrics to .lrc file</li>
  <li>Added preferenced dialog</li>
  <li>Added "Automatic File Manipulation" preference</li>
  <li>Files with the same names as songs and with .lrc extension now can be loaded and saved automatically on lines content change</li>
  <li>fix: library now scrolling vertically</li>
</ul>

## 0.1.3

<p>Bug fixes, new features</p>
<ul>
  <li>Added ability for one-shot syncing file</li>
</ul>

## 0.1.2

<p>Bug fixes</p>
<ul>
  <li>Read commit #4c95c8f for more information.</li>
</ul>

## 0.0.1

<p>Introduce i18n</p>
<ul>
  <li>Added internationalization. Contributors can use Hosted Weblate how transtating to their language.</li>
</ul>

## 0.1

<p>Initial release</p>
