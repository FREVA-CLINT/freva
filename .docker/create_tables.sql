-- MySQL dump 10.14  Distrib 5.5.68-MariaDB, for Linux (x86_64)
--
-- Host: www-regiklim.dkrz.de    Database: freva_dev
-- ------------------------------------------------------
-- Server version	5.5.68-MariaDB


--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
CREATE TABLE `auth_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
CREATE TABLE `auth_group_permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `group_id` (`group_id`,`permission_id`),
  KEY `auth_group_permissions_5f412f9a` (`group_id`),
  KEY `auth_group_permissions_83d7f98b` (`permission_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
CREATE TABLE `auth_permission` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `content_type_id` (`content_type_id`,`codename`),
  KEY `auth_permission_37ef4eb4` (`content_type_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `auth_user`
--

DROP TABLE IF EXISTS `auth_user`;
CREATE TABLE `auth_user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `auth_user_groups`
--

DROP TABLE IF EXISTS `auth_user_groups`;
CREATE TABLE `auth_user_groups` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`,`group_id`),
  KEY `auth_user_groups_6340c63c` (`user_id`),
  KEY `auth_user_groups_5f412f9a` (`group_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `auth_user_user_permissions`
--

DROP TABLE IF EXISTS `auth_user_user_permissions`;
CREATE TABLE `auth_user_user_permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`,`permission_id`),
  KEY `auth_user_user_permissions_6340c63c` (`user_id`),
  KEY `auth_user_user_permissions_83d7f98b` (`permission_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
CREATE TABLE `django_admin_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `action_time` datetime NOT NULL,
  `user_id` int(11) NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_6340c63c` (`user_id`),
  KEY `django_admin_log_37ef4eb4` (`content_type_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
CREATE TABLE `django_content_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `app_label` (`app_label`,`model`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `django_flatpage`
--

DROP TABLE IF EXISTS `django_flatpage`;
CREATE TABLE `django_flatpage` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `url` varchar(100) NOT NULL,
  `title` varchar(200) NOT NULL,
  `content` longtext NOT NULL,
  `enable_comments` tinyint(1) NOT NULL,
  `template_name` varchar(70) NOT NULL,
  `registration_required` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_flatpage_c379dc61` (`url`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `django_flatpage_sites`
--

DROP TABLE IF EXISTS `django_flatpage_sites`;
CREATE TABLE `django_flatpage_sites` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `flatpage_id` int(11) NOT NULL,
  `site_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `flatpage_id` (`flatpage_id`,`site_id`),
  KEY `django_flatpage_sites_872c4601` (`flatpage_id`),
  KEY `django_flatpage_sites_99732b5c` (`site_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
CREATE TABLE `django_migrations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_b7b81f0c` (`expire_date`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `django_site`
--

DROP TABLE IF EXISTS `django_site`;
CREATE TABLE `django_site` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `domain` varchar(100) NOT NULL,
  `name` varchar(50) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `externaluser_externaluser`
--

DROP TABLE IF EXISTS `externaluser_externaluser`;
CREATE TABLE `externaluser_externaluser` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `status` varchar(100) NOT NULL,
  `status_changed` datetime NOT NULL,
  `first_name` varchar(255) NOT NULL,
  `last_name` varchar(255) NOT NULL,
  `username` varchar(255) NOT NULL,
  `email` varchar(254) NOT NULL,
  `institute` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `externaluser_externaluser_email_63d2ae2521a190ae_uniq` (`email`),
  UNIQUE KEY `externaluser_externaluser_username_725969e832f7eabf_uniq` (`username`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `hindcast_frontend_hindcastevaluation`
--

DROP TABLE IF EXISTS `hindcast_frontend_hindcastevaluation`;
CREATE TABLE `hindcast_frontend_hindcastevaluation` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `score` varchar(50) NOT NULL,
  `eva_time_start` int(11) NOT NULL,
  `eva_time_end` int(11) NOT NULL,
  `region` varchar(255) NOT NULL,
  `time_frequency` varchar(255) NOT NULL,
  `variable` varchar(255) NOT NULL,
  `reference` varchar(255) NOT NULL,
  `hindcast_set` varchar(255) NOT NULL,
  `path_fieldmean` varchar(255) DEFAULT NULL,
  `path_map` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Table structure for table `history_configuration`
--

DROP TABLE IF EXISTS `history_configuration`;
CREATE TABLE `history_configuration` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `history_id_id` int(11) NOT NULL,
  `parameter_id_id` int(11) NOT NULL,
  `md5` varchar(32) NOT NULL,
  `value` longtext,
  `is_default` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `history_configuration_05e95c0f` (`history_id_id`),
  KEY `history_configuration_c3d9a846` (`parameter_id_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `history_history`
--

DROP TABLE IF EXISTS `history_history`;
CREATE TABLE `history_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `timestamp` datetime NOT NULL,
  `tool` varchar(50) NOT NULL,
  `version` varchar(20) NOT NULL,
  `configuration` longtext NOT NULL,
  `slurm_output` longtext NOT NULL,
  `uid` varchar(30) NOT NULL,
  `status` int(11) NOT NULL,
  `flag` int(11) NOT NULL DEFAULT '0',
  `version_details_id` int(11) NOT NULL DEFAULT '1',
  `caption` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `history_history_82ae9392` (`uid`),
  KEY `version_details_id` (`version_details_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `history_historytag`
--

DROP TABLE IF EXISTS `history_historytag`;
CREATE TABLE `history_historytag` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `history_id_id` int(11) NOT NULL,
  `type` int(11) NOT NULL,
  `text` longtext NOT NULL,
  `uid` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `history_historytag_05e95c0f` (`history_id_id`),
  KEY `history_historytag_82ae9392` (`uid`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `history_result`
--

DROP TABLE IF EXISTS `history_result`;
CREATE TABLE `history_result` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `history_id_id` int(11) NOT NULL,
  `output_file` longtext NOT NULL,
  `file_type` int(11) NOT NULL,
  `preview_file` longtext NOT NULL,
  PRIMARY KEY (`id`),
  KEY `history_result_05e95c0f` (`history_id_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `history_resulttag`
--

DROP TABLE IF EXISTS `history_resulttag`;
CREATE TABLE `history_resulttag` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `result_id_id` int(11) NOT NULL,
  `type` int(11) NOT NULL,
  `text` longtext NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `plugins_parameter`
--

DROP TABLE IF EXISTS `plugins_parameter`;
CREATE TABLE `plugins_parameter` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `parameter_name` varchar(50) NOT NULL,
  `parameter_type` varchar(50) NOT NULL,
  `tool` varchar(50) NOT NULL,
  `version` varchar(20) NOT NULL,
  `mandatory` tinyint(1) NOT NULL,
  `default` varchar(255) DEFAULT NULL,
  `impact` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `plugins_toolpullrequest`
--

DROP TABLE IF EXISTS `plugins_toolpullrequest`;
CREATE TABLE `plugins_toolpullrequest` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `created` datetime NOT NULL,
  `tool` varchar(50) NOT NULL,
  `tagged_version` varchar(50) NOT NULL,
  `status` varchar(10) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Table structure for table `plugins_version`
--

DROP TABLE IF EXISTS `plugins_version`;
CREATE TABLE `plugins_version` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `timestamp` datetime NOT NULL,
  `tool` varchar(50) NOT NULL,
  `version` varchar(20) NOT NULL,
  `internal_version_tool` varchar(40) NOT NULL,
  `internal_version_api` varchar(40) NOT NULL,
  `repository` longtext NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `solr_usercrawl`
--

DROP TABLE IF EXISTS `solr_usercrawl`;
CREATE TABLE `solr_usercrawl` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `created` datetime NOT NULL,
  `status` varchar(10) NOT NULL,
  `user_id` int(11) NOT NULL,
  `path_to_crawl` varchar(1000) NOT NULL,
  `tar_file` varchar(255) NOT NULL,
  `ingest_msg` longtext NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id_refs_id_dc9f4a71` (`user_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;


-- Dump completed on 2021-05-27  9:47:37
