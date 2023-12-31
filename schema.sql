CREATE EXTENSION IF NOT EXISTS pg_trgm;


CREATE TABLE IF NOT EXISTS configs (
    guild BIGINT PRIMARY KEY,
    logging BIGINT,
    ping BIGINT,
    reaction VARCHAR(60) NOT NULL DEFAULT '<:GiftifyTada:1098640605065777313>',
    participants_reaction VARCHAR(60) NOT NULL DEFAULT '<:GiftifyParticipants:1120007285226360964>',
    color INT NOT NULL DEFAULT 13316165,
    button_style INT NOT NULL CHECK (button_style BETWEEN 1 AND 4) DEFAULT 1,
    bypass_roles BIGINT[] NOT NULL DEFAULT '{}',
    required_roles BIGINT[] NOT NULL DEFAULT '{}',
    blacklisted_roles BIGINT[] NOT NULL DEFAULT '{}',
    multiplier_roles JSONB NOT NULL DEFAULT '{}',
    managers BIGINT[] NOT NULL DEFAULT '{}',
    dm_winner BOOLEAN NOT NULL DEFAULT TRUE,
    dm_host BOOLEAN NOT NULL DEFAULT TRUE,
    end_message VARCHAR(255) NOT NULL DEFAULT '<:GiftifyTada:1098640605065777313> Congratulations, {winners}! You have won the giveaway of prize {prize}.',
    reroll_message VARCHAR(255) NOT NULL DEFAULT '<:GiftifyTada:1098640605065777313> Congratulations, {winners}! You have won the reroll of the giveaway of prize {prize}.',
    dm_message VARCHAR(255) NOT NULL DEFAULT 'Congratulations, {winner}! You are the winner of the {prize} giveaway.',
    dm_host_message VARCHAR(255) NOT NULL DEFAULT 'Your giveaway for {prize} has ended. The winners are:' || CHR(10) || '{winners}',
    gw_header VARCHAR(100) NOT NULL DEFAULT '<:GiftifyTada:1098640605065777313> **GIVEAWAY** <:GiftifyTada:1098640605065777313>',
    gw_end_header VARCHAR(100) NOT NULL DEFAULT '<:GiftifyTada:1098640605065777313> **GIVEAWAY ENDED** <:GiftifyTada:1098640605065777313>'
);

CREATE TABLE IF NOT EXISTS channel_configs (
    guild BIGINT,
    channel BIGINT,
    ping BIGINT,
    required_roles BIGINT[] NOT NULL DEFAULT '{}',
    blacklisted_roles BIGINT[] NOT NULL DEFAULT '{}',
    bypass_roles BIGINT[] NOT NULL DEFAULT '{}',
    multiplier_roles JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (guild, channel),
    FOREIGN KEY (guild) REFERENCES configs(guild) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_configs_guild ON configs (guild);
CREATE UNIQUE INDEX IF NOT EXISTS idx_channel_configs_guild_channel ON channel_configs (guild, channel);

CREATE TABLE IF NOT EXISTS timers (
    message BIGINT,
    channel BIGINT,
    guild BIGINT,
    author_id BIGINT NOT NULL,
    event TEXT NOT NULL,
    title VARCHAR(100) NOT NULL,
    expires TIMESTAMPTZ DEFAULT timezone('UTC', CURRENT_TIMESTAMP),
    PRIMARY KEY (guild, channel, message)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_timer_entry ON timers (guild, channel, message);

CREATE TABLE IF NOT EXISTS giveaways (
    guild BIGINT,
    channel BIGINT,
    message BIGINT,
    extra_message BIGINT, 
    prize VARCHAR(255) NOT NULL,
    host BIGINT NOT NULL,
    winner_count INT NOT NULL,
    winners BIGINT[] DEFAULT '{}'::BIGINT[],
    participants BIGINT[] DEFAULT '{}'::BIGINT[],
    ended BOOLEAN NOT NULL DEFAULT FALSE,
    ends TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, 
    required_roles BIGINT[] DEFAULT '{}'::BIGINT[],
    blacklisted_roles BIGINT[] DEFAULT '{}'::BIGINT[],
    bypass_roles BIGINT[] DEFAULT '{}'::BIGINT[],
    multiplier_roles JSONB DEFAULT '{}'::JSONB,
    messages JSONB DEFAULT '{}'::JSONB,
    messages_required INT DEFAULT 0,
    messages_channel BIGINT[],
    amari INT,
    weekly_amari INT,
    donor BIGINT,
    PRIMARY KEY (guild, channel, message),
    FOREIGN KEY (guild) REFERENCES configs(guild) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_giveaway ON giveaways (guild, channel, message);

CREATE TABLE IF NOT EXISTS stats (
  host BIGINT,
  guild BIGINT,
  count INT DEFAULT 0,
  PRIMARY KEY (guild, host)
);

CREATE INDEX IF NOT EXISTS idx_stats_guild_id ON stats (guild);

CREATE OR REPLACE FUNCTION update_stats()
  RETURNS TRIGGER AS $$
BEGIN

  INSERT INTO stats (guild, host, count)
  VALUES (NEW.guild, NEW.host, 1)
  ON CONFLICT (guild, host)
  DO UPDATE SET count = stats.count + 1;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS increment_stats_insert_trigger ON giveaways;
CREATE TRIGGER increment_stats_insert_trigger
AFTER INSERT ON giveaways
FOR EACH ROW
EXECUTE FUNCTION update_stats();

CREATE OR REPLACE FUNCTION decrement_stats()
  RETURNS TRIGGER AS $$
BEGIN

  UPDATE stats
  SET count = count - 1
  WHERE guild = OLD.guild AND host = OLD.host;
  
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS decrement_stats_delete_trigger ON giveaways;
CREATE TRIGGER decrement_stats_delete_trigger
AFTER DELETE ON giveaways
FOR EACH ROW
EXECUTE FUNCTION decrement_stats();

CREATE TABLE IF NOT EXISTS donation_configs (
  guild BIGINT,
  category VARCHAR(50),
  symbol CHAR(1) NOT NULL DEFAULT '$',
  roles JSONB DEFAULT '{}'::JSONB,
  managers BIGINT[] DEFAULT '{}'::BIGINT[],
  logging BIGINT,
  PRIMARY KEY (guild, category)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_donation_configs ON donation_configs (guild, category);

CREATE TABLE IF NOT EXISTS donations (
  member BIGINT,
  guild BIGINT,
  category VARCHAR(50),
  amount BIGINT NOT NULL DEFAULT 0,
  PRIMARY KEY (member, guild, category),
  FOREIGN KEY (guild, category) REFERENCES donation_configs(guild, category) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_donations ON donations (member, guild, category);

CREATE TABLE IF NOT EXISTS raffles (
  guild BIGINT,
  name VARCHAR(50),
  winner BIGINT,
  deputy_roles BIGINT[] DEFAULT '{}'::BIGINT[],
  deputy_members BIGINT[] DEFAULT '{}'::BIGINT[],
  tickets JSONB DEFAULT '{}'::JSONB,
  PRIMARY KEY (guild, name)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_raffles ON raffles (guild, name);