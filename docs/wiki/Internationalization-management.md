_Update: Development team, 8-Oct-2024_

### Introduction

This guide explains how to generate files with translatable terms and how to complete them with translations.

### Preparation

Obtain a copy of the project from GitHub by running the following command:

```
git clone git@github.com:scieloorg/opac_5.git
```

### How to create files with translatable terms

Run the following command:

```
export LANG=pt && make create_catalog
```

The result of this command is the creation of a new file in the _translations_ folder:

![Screenshot 2024-08-05 at 16 38 50](https://github.com/user-attachments/assets/c882c03a-2297-4b81-aa3b-24549380c0f3)

### How to update files with translatable terms

Run the following command:

```
make update_catalog
```

The result of this command is the creation or update of the .po files:

![Screenshot 2024-08-05 at 16 40 40](https://github.com/user-attachments/assets/e632dbc1-aeae-4049-b72b-be5b0983be24)

### The .po files (translation files)

These files follow the pattern below:

#### Header

```
# FIRST AUTHOR <email@address>, YEAR.
#
msgid ""
msgstr ""
"Project-Id-Version: Transifex\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2018-03-29 12:41+0000\n"
"PO-Revision-Date: 2018-03-29 12:43+0000\n"
"Last-Translator: Transifex\n"
"Language-Team: English (https://app.transifex.com/transifex/transifex/language/en/)\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Language: en\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"
```

#### Body

A sequence of original terms (msgid) and translations (msgstr):

```
#: actionlog/templates/object_action_list.html:7 txpermissions/forms.py:18
msgid "User"
msgstr ""

#: actionlog/templates/object_action_list.html:8
msgid "Action"
msgstr ""
```

### How to compile files with translated terms

Run the following command:

```
make compile_messages
```

This compiles the translations from .po files into .mo files ready for use.

Result of this command:

![Screenshot 2024-08-05 at 16 44 32](https://github.com/user-attachments/assets/5c8f4df0-9117-4fb9-8ef4-2d2e5fb7da81)

### How to complete the translations

The files to be edited are messages.po. You can edit the translation files in any text editor.

They are located at [https://github.com/scieloorg/opac_5/tree/master/opac/webapp/translations](https://github.com/scieloorg/opac_5/tree/master/opac/webapp/translations), in folders named after their respective languages ("en", "es", "es_MX", "es_ES", "pt_BR").

The `msgstr ""` lines should be completed with the respective translation. For example:

**Before**

```
#: actionlog/templates/object_action_list.html:7 txpermissions/forms.py:18
msgid "User"
msgstr ""

#: actionlog/templates/object_action_list.html:8
msgid "Action"
msgstr ""
```

**After**

```
#: actionlog/templates/object_action_list.html:7 txpermissions/forms.py:18
msgid "User"
msgstr "Usuário"

#: actionlog/templates/object_action_list.html:8
msgid "Action"
msgstr "Ação"
```

### How to update translations in the project

After completing the translation, open a Pull Request with the changes to the project.

### How to add a new language to the interface

After completing all the procedures for creating translation files, you can enable a new language in the interface by adding a new entry to the environment variable file _.flask_:

Default definition of the .flask file for the OPAC_LANGUAGES variable:

```
OPAC_LANGUAGES="{'pt_BR': 'Português','en': 'English','es': 'Español'}"
```

To add a new language that already has its translations, you need to modify this variable. For example, to add Italian:

```
OPAC_LANGUAGES="{'pt_BR': 'Português','en': 'English','es': 'Español', 'it': 'Italian'}"
```

### How to contribute without using git

This procedure is recommended for those who only want to perform the translation, while the incorporation procedures are the responsibility of the SciELO development team.

Access the folder [https://github.com/scieloorg/opac_5/tree/master/opac/webapp/translations](https://github.com/scieloorg/opac_5/tree/master/opac/webapp/translations) through GitHub and copy the .po file. See the image below for how to download this file:

![Screenshot 2024-08-16 at 07 32 10](https://github.com/user-attachments/assets/77c854f6-7ed2-4281-9e81-29cb4d3be8b6)

If the files do not exist, send an email requesting the files for a new language.

To edit the file directly on GitHub, you need a GitHub account. See the link with instructions to create an account: [https://docs.github.com/en/get-started/start-your-journey/creating-an-account-on-github](https://docs.github.com/en/get-started/start-your-journey/creating-an-account-on-github)

You can edit the file by clicking the edit link as shown in the image:

![Screenshot 2024-08-19 at 07 28 07](https://github.com/user-attachments/assets/9d550398-a5c3-4790-83d9-0abc31a31906)

Perform the translation of the .po file.

After completing the translation, send an email requesting the incorporation of the translation.
