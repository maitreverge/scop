/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   font.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tde-los- <tde-los-@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/05/16 14:44:59 by tde-los-          #+#    #+#             */
/*   Updated: 2024/05/16 16:45:29 by tde-los-         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

# include "../includes/include.h"

void    font_create(s_font *font, char *file)
{
    s_font  *temp;

    if (!file)
    {
        printf("Font error: 'NULL' ❌\n");
        return ;
    }
    temp = font_next(font);
    if (!temp)
        printf("error\n");
    temp->name = ft_strdup(file);
    temp->font = TTF_OpenFont(file, 24);
    if (!temp->font)
    {
        printf("Font error: %s can\'t be load ❌\n", file);
        return ;
    }
    printf("Font loaded successfully: %s ✅\n", temp->name);
}

s_font  *get_font(s_font *font, char *name)
{
    s_font  *temp = font->next;

    while (temp)
    {
        if (!strcmp(temp->name, name))
            return (temp);
        temp = temp->next;
    }
    return (NULL);
}

void	free_font(s_font *lst)
{
    s_font	*current;
    s_font	*next;

	printf("\n\t[Free font 🖍️ ]\n\n");
	if (!lst)
		return ;
	current = lst->next;
    while (current != NULL)
	{
        next = current->next;
		if (current->name && current->font)
			ft_printf("Font successfully free: %s ⬜\n", current->name);
		if (current->name)
            free(current->name);
		if (current->font)
            TTF_CloseFont(current->font);
        free(current);
        current = next;
    }
}

void    font_lib(s_font *font)
{
    printf("\n\t[Loading font 🖍️ ]\n\n");
    font_create(font, ARIAL);
    font_create(font, CARNIVAL);
	font_create(font, FRANCHISE);
    font_create(font, MAGIC_RETRO);
    font_create(font, NAMECAT);
    font_create(font, SUPER_RETRO);
	font_create(font, NULL);
    font_create(font, "TEST_ERROR");
}

void	init_font(s_font *font)
{
	TTF_Init();
    font->next = NULL;
    font->id = 0;
    font_lib(font);
}

//*	Fonction ajoute un font en fin de liste (struct font->next)

s_font	*font_next(s_font *lst)
{
	s_font	*new;
	s_font	*temp;

	if (!lst)
		return (NULL);
	temp = lst;
	while (temp->next)
		temp = temp->next;
	new = (s_font *)ft_calloc(sizeof(s_font), 1);
	*new = (s_font){.font = NULL, .id = temp->id + 1, .name = NULL};
	if (!new)
		return (NULL);
	new->next = NULL;
	temp->next = new;
	return (new);
}