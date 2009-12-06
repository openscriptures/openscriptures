
mysqldump -u root -p --no-create-info --compact --skip-add-drop-table --databases oss_core --tables core_ref core_token core_tokenparsing core_work > supplemental_data.sql