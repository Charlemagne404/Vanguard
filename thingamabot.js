const { Client, GatewayIntentBits, PermissionsBitField } = require('discord.js');
const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent] });

const LOCKDOWN_ROLE_NAME = 'Member'; // the role everyone has
const MOD_ROLES = ['Mod', 'Admin']; // roles that can bypass lockdown

client.on('messageCreate', async message => {
    if (!message.guild) return;

    // Lockdown command
    if (message.content === '!lockdown') {
        if (!message.member.roles.cache.some(r => MOD_ROLES.includes(r.name))) return;

        const role = message.guild.roles.cache.find(r => r.name === LOCKDOWN_ROLE_NAME);
        if (!role) return message.channel.send('Role not found.');

        message.guild.channels.cache.forEach(channel => {
            channel.permissionOverwrites.edit(role, {
                SendMessages: false,
                AddReactions: false,
                Connect: false // for voice channels
            });
        });

        message.channel.send('Server is now in lockdown!');
    }

    // Unlock command
    if (message.content === '!unlock') {
        if (!message.member.roles.cache.some(r => MOD_ROLES.includes(r.name))) return;

        const role = message.guild.roles.cache.find(r => r.name === LOCKDOWN_ROLE_NAME);
        if (!role) return message.channel.send('Role not found.');

        message.guild.channels.cache.forEach(channel => {
            channel.permissionOverwrites.edit(role, {
                SendMessages: true,
                AddReactions: true,
                Connect: true
            });
        });

        message.channel.send('Lockdown lifted!');
    }
});

client.login('REDACTED_TOKEN');
